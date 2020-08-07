import logging
import string
import requests
import xml.etree.ElementTree as ET
from homeassistant.helpers.entity import Entity
from datetime import timedelta

SCAN_INTERVAL = timedelta(minutes=5)
_LOGGER = logging.getLogger(__name__)
#logging.basicConfig(level=logging.DEBUG)

DOMAIN = 'bchydro'
URL_LOGIN = "https://app.bchydro.com/sso/UI/Login"
URL_GET_USAGE = "https://app.bchydro.com/evportlet/web/account-profile-data.html"
URL_ACCT_INFO = "https://app.bchydro.com/evportlet/web/global-data.html"

# DO NOT PUBLISH THIS FILE WITH THESE VARS FILLED OUT!!
#   Update these 2 variables with your BCHydro username and password if you
#   absolutely need to hack this together...
bchydro_username = "email"
bchydro_password = "pw"


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the sensor platform."""
    # How do we get secrets from HASS passed in here?
    # Should the API be instantiated here, or later in each sensor?
    api = BCHydroApi(bchydro_username, bchydro_password)
    add_entities([BCHydroUsageSensor(api)])


class BCHydroUsageSensor(Entity):
    def __init__(self, api):
        """Initialize the sensor."""
        self._api = api
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'BC Hydro Usage'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        return 'kWh'

    def update(self):
        """Fetch new state data for the sensor."""
        latest = self._api.latest_usage()
        self._state = latest


class BCHydroApi:
    def __init__(self, username, password):
        """Initialize the sensor."""
        self.username = username
        self.password = password
        self._account_number = None
        self._slid = None
        self._cookies = None
        self.login()


    def call_api(self, method, url, **kwargs):
        payload = kwargs.get("params") or kwargs.get("data")
        _LOGGER.debug("About to call %s with payload=%s", url, payload)
        response = requests.request(
            method,
            url,
            timeout = 10,
            cookies = self._cookies,
            allow_redirects = False,
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
                'email': self.username,
                'password': self.password,
                'gotoUrl': "https://app.bchydro.com:443/BCHCustomerPortal/web/login.html"
            }
        )
        jar = request.cookies
        iterationNumber = 1

        # Follow login redirects until landed.
        # Collect cookies in a jar for subsequent API requests.
        while request.status_code == 302:
            iterationNumber += 1
            redirect_URL2 = request.headers['Location']
            request = requests.get(redirect_URL2, cookies=jar)
            jar.update(request.cookies)
    
        _LOGGER.debug("Redirect iterations: %s", iterationNumber)
        self._cookies = jar
        
        # Now that we have session cookies, let's fetch the actual account nums
        try:
            request = self.call_api("get", URL_ACCT_INFO)
            json = request.json()
            self._slid = json['evpSlid']
            self._account_number = json['evpAccount'].lstrip("0")

        except Exception as e:
            _LOGGER.error("SLID/Account Number parse error: %s", e)
            raise


    def latest_usage(self):
        """Fetch new state data for the sensor."""
        latest_usage = None

        response = self.call_api(
            "get",
            URL_GET_USAGE,
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "Slid": self._slid,
                "Account": self._account_number,
                "ValidityStart": '2015-09-03T00:00:00.000-07:00',
                "ValidityEnd": '9999-12-31T00:00:00.000-08:00'
            }
        )

        try:
            resultingCleanString = ''.join(filter(lambda x: x in string.printable, response.text))
            root = ET.fromstring(resultingCleanString)

            for point in root.findall('Series')[0].findall('Point'):
                # Todo: == 'ACTUAL', and ensure the date matches now
                if point.get('quality') != 'INVALID':
                    latest_usage = point.get('value')
                    _LOGGER.debug("Found point: %s", latest_usage)


        except ET.ParseError:
            _LOGGER.error("Unable to parse XML from string")
        except IndexError:
            _LOGGER.error("Usage data malformed: couldn't find point series")
        except Exception as e:
            _LOGGER.error("Usage data malformed: unexpected error: %s", e)
            raise

        return latest_usage
