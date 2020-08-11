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
from . import BCHydroEnergyDeviceEntity

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)

SCAN_INTERVAL = timedelta(minutes=5)
#PARALLEL_UPDATES = 4
_LOGGER = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

DOMAIN = "bchydro"


async def async_setup_entry(hass, entry, async_add_entities):

    # def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the sensor platform."""
    bchydro_username = config[CONF_USERNAME]
    bchydro_password = config.get(CONF_PASSWORD)
    api = BCHydroApi()

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(10):
                await api.authenticate(bchydro_username, bchydro_password)
                return await api.fetch_data()
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="sensor",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    # async_add_entities(MyEntity(coordinator, idx) for idx, ent
    #                    in enumerate(coordinator.data))
    async_add_entities([
        MyEntity(coordinator, api)
    ])



class BCHydroEnergySensor(BCHydroEnergyDeviceEntity):
    """Defines a BCHydro Energy sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: BCHydroApi,
        key: str,
        name: str,
        icon: str,
        unit_of_measurement: str = "",
    ) -> None:
        """Initialize OVO Energy sensor."""
        self._unit_of_measurement = unit_of_measurement

        super().__init__(coordinator, client, key, name, icon)

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement


class BCHydroEnergyLastElectricityReading(BCHydroEnergySensor):
    """Defines a OVO Energy last reading sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, client: BCHydro):
        """Initialize OVO Energy sensor."""

        super().__init__(
            coordinator,
            client,
            f"{client.account_id}_last_electricity_reading",
            "OVO Last Electricity Reading",
            "mdi:flash",
            "kWh",
        )

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        # HERE!!
        # Next steps:
        # reformat BCHydroApi data to match the OVO data
        # ie. set usage.electricity[].consumption
        usage: OVODailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return usage.electricity[-1].consumption

    @property
    def device_state_attributes(self) -> object:
        """Return the attributes of the sensor."""
        usage: OVODailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return {
            "start_time": usage.electricity[-1].interval.start,
            "end_time": usage.electricity[-1].interval.end,
        }
















    # add_entities(
    #     [
    #         BCHydroSensor(
    #             api,
    #             "latest_usage",
    #             "Latest Usage",
    #             DEVICE_CLASS_POWER,
    #             ENERGY_KILO_WATT_HOUR,
    #         ),
    #         BCHydroSensor(
    #             api,
    #             "consumption_to_date",
    #             "Consumption to Date",
    #             DEVICE_CLASS_POWER,
    #             ENERGY_KILO_WATT_HOUR,
    #         ),
    #         BCHydroSensor(
    #             api,
    #             "cost_to_date",
    #             "Cost to Date",
    #             "expense",  # no class for "cost"?
    #             "$",
    #         ),
    #         BCHydroSensor(
    #             api, "billing_period_end", "Next Billing Period", ATTR_DATE, ""
    #         ),
    #     ]
    # )


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
