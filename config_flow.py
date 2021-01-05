"""Config flow to configure the BCHydro integration."""
import logging

import aiohttp
from bchydro import BCHydroApi
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_ACCOUNT_ID, DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


class BCHydroFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a BCHydro config flow."""
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self.data_schema = {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        }

        self._password = None
        self._username = None
        self._account_id = None

    async def _async_bchydro_login(self, step_id):
        """Handle login with BCHydro."""
        errors = {}

        try:
            client = BCHydroApi(self._username, self._password)
            await client.refresh()

        except Exception as ex:
            _LOGGER.error("Unable to connect to BCHydro: %s", ex)
            errors = {"base": "cannot_connect"}

        if errors:
            return self.async_show_form(
                step_id=step_id, data_schema=vol.Schema(self.data_schema), errors=errors
            )

        return await self._async_create_entry()

    async def _async_create_entry(self):
        """Create the config entry."""
        config_data = {
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_ACCOUNT_ID: self._account_id,
        }
        existing_entry = await self.async_set_unique_id(self._username)

        if existing_entry:
            self.hass.config_entries.async_update_entry(
                existing_entry, data=config_data
            )
            # Reload the BCHydro config entry otherwise account will remain unavailable
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(existing_entry.entry_id)
            )

            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(title=self._username, data=config_data)


    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(self.data_schema)
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        return await self._async_bchydro_login(step_id="user")

    async def async_step_reauth(self, config):
        """Handle reauthorization request from BCHydro."""
        self._username = config[CONF_USERNAME]

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Handle reauthorization flow."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_USERNAME, default=self._username): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
            )

        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        return await self._async_bchydro_login(step_id="reauth_confirm")

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        if self._async_current_entries():
            _LOGGER.warning("Already configured. Only a single configuration possible.")
            return self.async_abort(reason="single_instance_allowed")

        self._account_id = import_config.get(CONF_ACCOUNT_ID, False)

        return await self.async_step_user(import_config)
