import logging
import string
import requests
from datetime import timedelta
import xml.etree.ElementTree as ET
import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.const import DEVICE_CLASS_POWER, ENERGY_KILO_WATT_HOUR, ATTR_DATE
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME


# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)

SCAN_INTERVAL = timedelta(minutes=5)
_LOGGER = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

DOMAIN = "bchydro"
URL_LOGIN = "https://app.bchydro.com/sso/UI/Login"
URL_ACCT_INFO = "https://app.bchydro.com/evportlet/web/global-data.html"
URL_GET_USAGE = "https://app.bchydro.com/evportlet/web/account-profile-data.html"

# This URL has more detail than URL_GET_USAGE but seems to require more headers to access.
# Not used at the moment, but ideally it will replace URL_GET_USAGE.
# URL_GET_CONSUMPTION = "https://app.bchydro.com/evportlet/web/consumption-data.html"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the sensor platform."""
    bchydro_username = config[CONF_USERNAME]
    bchydro_password = config.get(CONF_PASSWORD)
    api = BCHydroApi(bchydro_username, bchydro_password)

    add_entities(
        [
            BCHydroSensor(
                api,
                "latest_usage",
                "Latest Usage",
                DEVICE_CLASS_POWER,
                ENERGY_KILO_WATT_HOUR,
            ),
            BCHydroSensor(
                api,
                "consumption_to_date",
                "Consumption to Date",
                DEVICE_CLASS_POWER,
                ENERGY_KILO_WATT_HOUR,
            ),
            BCHydroSensor(
                api,
                "cost_to_date",
                "Cost to Date",
                "expense",  # no class for "cost"?
                "$",
            ),
            BCHydroSensor(
                api, "billing_period_end", "Next Billing Period", ATTR_DATE, ""
            ),
        ]
    )


class BCHydroSensor(Entity):
    def __init__(self, api, unique_id, name, device_class, unit_of_measurement):
        """Initialize the sensor."""
        self._api = api
        self._unique_id = unique_id
        self._name = name
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
        }

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        return self._unit_of_measurement

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._unique_id == "latest_usage":
            return self._api.get_latest_usage()

        elif self._unique_id == "consumption_to_date":
            return self._api.data.get("rates").get("consumption_to_date")

        elif self._unique_id == "cost_to_date":
            return self._api.data.get("rates").get("cost_to_date")

        elif self._unique_id == "billing_period_end":
            return self._api.data.get("rates").get("billing_period_end")

    def update(self):
        # Todo: move this to an api in __init__.py
        self._api.login()
        self._api.fetch_data()


class BCHydroApi:
    def __init__(self, username, password):
        """Initialize the sensor."""
        self.username = username
        self.password = password
        self._account_number = None
        self._slid = None
        self._cookies = None
        self.data = {"usage": [], "rates": {}}

    def call_api(self, method, url, **kwargs):
        payload = kwargs.get("params") or kwargs.get("data")
        _LOGGER.debug("About to call %s with payload=%s", url, payload)
        response = requests.request(
            method,
            url,
            timeout=10,
            cookies=self._cookies,
            allow_redirects=False,
            **kwargs
        )

        response.raise_for_status()
        return response

    def login(self):
        request = self.call_api(
            "post",
            URL_LOGIN,
            data={
                "realm": "bch-ps",
                "email": self.username,
                "password": self.password,
                "gotoUrl": "https://app.bchydro.com:443/BCHCustomerPortal/web/login.html",
            },
        )
        jar = request.cookies
        iterationNumber = 1

        # Follow login redirects until landed.
        # Collect cookies in a jar for subsequent API requests.
        while request.status_code == 302:
            iterationNumber += 1
            redirect_URL2 = request.headers["Location"]
            request = requests.get(redirect_URL2, cookies=jar)
            jar.update(request.cookies)

        _LOGGER.debug("Redirect iterations: %s", iterationNumber)
        self._cookies = jar

        # Now that we have session cookies, let's fetch the actual account nums
        try:
            request = self.call_api("get", URL_ACCT_INFO)
            json = request.json()
            self._slid = json["evpSlid"]
            self._account_number = json["evpAccount"].lstrip("0")

        except Exception as e:
            _LOGGER.error("SLID/Account Number parse error: %s", e)
            raise

    def fetch_data(self):
        """Fetch new state data to store on the API"""
        response = self.call_api("get", URL_GET_USAGE)
        new_usage = []

        try:
            resultingCleanString = "".join(
                filter(lambda x: x in string.printable, response.text)
            )
            root = ET.fromstring(resultingCleanString)

            for point in root.findall("Series")[0].findall("Point"):
                # Todo: == 'ACTUAL', and ensure the date matches now
                if point.get("quality") != "INVALID":
                    new_usage.append(
                        {
                            "quality": point.get("quality"),
                            "value": point.get("value"),
                            "cost": point.get("cost"),
                        }
                    )
            self.data["usage"] = new_usage

        except ET.ParseError as e:
            _LOGGER.error("Unable to parse XML from string: %s", e)
        except IndexError as e:
            _LOGGER.error("Usage data malformed: couldn't find point series: %s", e)
        except Exception as e:
            _LOGGER.error("Usage data malformed: unexpected error: %s", e)
            raise

        try:
            rates = root.find("Rates")
            self.data["rates"] = {
                "billing_period_start": rates.get("bpStart"),
                "billing_period_end": rates.get("bpEnd"),
                "consumption_to_date": rates.get("cons2date").strip("kWh"),
                "cost_to_date": rates.get("cost2date").strip("$"),
                "estimated_consumption": rates.get("estCons").strip("kWh"),
                "estimated_cost": rates.get("estCost").strip("$"),
            }
        except Exception as e:
            _LOGGER.error("Data reformatting error: %s", e)
            raise

        return self.data

    def get_latest_usage(self):
        return self.data["usage"][-1]["value"] if len(self.data["usage"]) else None

    def get_latest_cost(self):
        return self.data["usage"][-1]["cost"] if len(self.data["usage"]) else None
