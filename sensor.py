import logging
from datetime import timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from bchydro import BCHydroApi, BCHydroDailyUsage
from . import BCHydroDeviceEntity
from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN


# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_USERNAME): cv.string, vol.Required(CONF_PASSWORD): cv.string}
)

SCAN_INTERVAL = timedelta(seconds=300)
PARALLEL_UPDATES = 4

_LOGGER = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up a BCHydro sensor based on a config entry."""
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    client: BCHydroApi = hass.data[DOMAIN][entry.entry_id][DATA_CLIENT]

    async_add_entities(
        [
            BCHydroLatestUsage(coordinator, client),
            BCHydroLatestCost(coordinator, client),
            BCHydroEstimatedUsage(coordinator, client),
            BCHydroEstimatedCost(coordinator, client),
        ]
    )


class BCHydroSensor(BCHydroDeviceEntity):
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
        """Initialize BCHydro sensor."""
        self._unit_of_measurement = unit_of_measurement

        super().__init__(coordinator, client, key, name, icon)

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit this state is expressed in."""
        return self._unit_of_measurement


class BCHydroLatestUsage(BCHydroSensor):
    """Defines a BCHydro latest usage sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, client: BCHydroApi):
        """Initialize BCHydro sensor."""

        super().__init__(
            coordinator,
            client,
            f"{client.account.evpSlid}_latest_usage",
            "BCHydro Latest Usage Reading",
            "mdi:flash",
            "kWh",
        )

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return usage.electricity[-1].consumption

    @property
    def device_state_attributes(self) -> object:
        """Return the attributes of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return {
            "start_time": usage.electricity[-1].interval.start,
            "end_time": usage.electricity[-1].interval.end,
        }


class BCHydroLatestCost(BCHydroSensor):
    """Defines a BCHydro latest usage sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, client: BCHydroApi):
        """Initialize BCHydro sensor."""

        super().__init__(
            coordinator,
            client,
            f"{client.account.evpSlid}_latest_cost",
            "BCHydro Latest Cost Reading",
            "mdi:currency-usd",
            "$",
        )

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return usage.electricity[-1].cost

    @property
    def device_state_attributes(self) -> object:
        """Return the attributes of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.electricity:
            return None
        return {
            "start_time": usage.electricity[-1].interval.start,
            "end_time": usage.electricity[-1].interval.end,
        }


class BCHydroEstimatedUsage(BCHydroSensor):
    """Defines a BCHydro latest usage sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, client: BCHydroApi):
        """Initialize BCHydro sensor."""

        super().__init__(
            coordinator,
            client,
            f"{client.account.evpSlid}_estimated_usage",
            "BCHydro Estimated Usage Reading",
            "mdi:flash",
            "kWh",
        )

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.rates:
            return None
        return usage.rates.estimated_consumption

    @property
    def device_state_attributes(self) -> object:
        """Return the attributes of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.rates:
            return None
        return {
            "start_time": usage.electricity[-1].interval.start,
            "end_time": usage.electricity[-1].interval.end,
        }


class BCHydroEstimatedCost(BCHydroSensor):
    """Defines a BCHydro latest usage sensor."""

    def __init__(self, coordinator: DataUpdateCoordinator, client: BCHydroApi):
        """Initialize BCHydro sensor."""

        super().__init__(
            coordinator,
            client,
            f"{client.account.evpSlid}_estimated_cost",
            "BCHydro Estimated Cost Reading",
            "mdi:currency-usd",
            "$",
        )

    @property
    def state(self) -> str:
        """Return the state of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.rates:
            return None
        return usage.rates.estimated_cost

    @property
    def device_state_attributes(self) -> object:
        """Return the attributes of the sensor."""
        usage: BCHydroDailyUsage = self._coordinator.data
        if usage is None or not usage.rates:
            return None
        return {
            "start_time": usage.electricity[-1].interval.start,
            "end_time": usage.electricity[-1].interval.end,
        }
