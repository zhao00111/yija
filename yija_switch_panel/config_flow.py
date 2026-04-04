"""Config flow for Yija Switch panel."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_WEATHER_ENTITY_ID,
    DEFAULT_WEATHER_ENTITY_ID,
    DOMAIN,
    INTEGRATION_NAME,
)


class TuyaRelayNamesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yija Switch panel."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=INTEGRATION_NAME, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_build_schema())

    @staticmethod
    def async_get_options_flow(config_entry):
        return TuyaRelayNamesOptionsFlow(config_entry)


class TuyaRelayNamesOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Yija Switch panel."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                self.config_entry.options.get(
                    CONF_WEATHER_ENTITY_ID,
                    self.config_entry.data.get(CONF_WEATHER_ENTITY_ID, DEFAULT_WEATHER_ENTITY_ID),
                )
            ),
        )


def _build_schema(default_weather_entity_id: str = DEFAULT_WEATHER_ENTITY_ID):
    return vol.Schema(
        {
            vol.Optional(
                CONF_WEATHER_ENTITY_ID,
                default=default_weather_entity_id,
                description={
                    "suggested_value": default_weather_entity_id,
                },
            ): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))
        }
    )
