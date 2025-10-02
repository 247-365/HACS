from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from . import DOMAIN, CONF_BEARER_TOKEN

class OllamaOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            CONF_BEARER_TOKEN: self.config_entry.options.get(CONF_BEARER_TOKEN, ""),
        }

        schema = vol.Schema(
            {
                vol.Optional(CONF_BEARER_TOKEN, default=defaults[CONF_BEARER_TOKEN]): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

@callback
def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return OllamaOptionsFlowHandler(config_entry)
