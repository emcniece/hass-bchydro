"""The BCHydro sensor integration."""
import logging
from typing import Any, Dict
import aiohttp
import async_timeout
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DATA_CLIENT, DATA_COORDINATOR, DOMAIN

from bchydro import BCHydroApi, BCHydroDailyUsage

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    """Set up the BCHdydro components."""
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    """Set up BCHdydro from a config entry."""

    client = BCHydroApi()

    try:
        await client.authenticate(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
    except aiohttp.ClientError as exception:
        _LOGGER.warning(exception)
        raise ConfigEntryNotReady from exception

    async def async_update_data() -> BCHydroDailyUsage:
        """Fetch data from BCHydro."""
        async with async_timeout.timeout(10):
            return await client.get_daily_usage()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="sensor",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=300),
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_CLIENT: client,
        DATA_COORDINATOR: coordinator,
    }

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    # Setup components
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistantType, entry: ConfigType) -> bool:
    """Unload BCHydro config entry."""
    # Unload sensors
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    del hass.data[DOMAIN][entry.entry_id]

    return True


class BCHydroEntity(Entity):
    """Defines a base BCHydro entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: BCHydroApi,
        key: str,
        name: str,
        icon: str,
    ) -> None:
        """Initialize the BCHydro entity."""
        self._coordinator = coordinator
        self._client = client
        self._key = key
        self._name = name
        self._icon = icon
        self._available = True

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this sensor."""
        return self._key

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self) -> str:
        """Return the mdi icon of the entity."""
        return self._icon

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._coordinator.last_update_success and self._available

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    async def async_update(self) -> None:
        """Update BCHydro entity."""
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self) -> None:
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )


class BCHydroDeviceEntity(BCHydroEntity):
    """Defines a BCHydro device entity."""

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information about this BCHydro instance."""
        return {
            "identifiers": {(DOMAIN, self._client.account.evpSlid)},
            "manufacturer": "BCHydro",
            "model": "0.4",
            "name": "BCHydro Readings",
            "entry_type": "service",
        }
