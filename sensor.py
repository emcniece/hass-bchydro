import logging
import async_timeout
from datetime import timedelta
import voluptuous as vol
from homeassistant.helpers.entity import Entity
from homeassistant.const import DEVICE_CLASS_POWER, ENERGY_KILO_WATT_HOUR, ATTR_DATE
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from api import BCHydroApi

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)

SCAN_INTERVAL = timedelta(minutes=5)
_LOGGER = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

DOMAIN = "bchydro"


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
