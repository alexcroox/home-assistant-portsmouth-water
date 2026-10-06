"""Sign in once; save a refresh token, never the password."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import Client, AuthError, ApiError
from .const import DOMAIN, CONF_UNIT, DEFAULT_UNIT, UNITS

class Flow(config_entries.ConfigFlow,domain=DOMAIN):
    VERSION=1
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()
    async def async_step_user(self,user_input=None):
        errors={}
        if user_input:
            api=Client(async_get_clientsession(self.hass))
            try:
                await api.login(user_input["email"],user_input["password"])
                self.accounts=await api.accounts()
                if not self.accounts: return self.async_abort(reason="no_accounts")
                self.login_data={"email":user_input["email"],"refresh_token":api.refresh_token}
                if not api.refresh_token: return self.async_abort(reason="no_refresh_token")
                if len(self.accounts)==1:
                    return await self.async_step_account({"account":self.accounts[0]["number"]})
                return await self.async_step_account()
            except AuthError: errors["base"]="invalid_auth"
            except ApiError: errors["base"]="cannot_connect"
        return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required("email"):str,vol.Required("password"):str}),errors=errors)
    async def async_step_account(self,user_input=None):
        if user_input:
            account=user_input["account"]
            if self.source == config_entries.SOURCE_REAUTH and account != self._get_reauth_entry().data["account"]:
                return self.async_abort(reason="wrong_account")
            if account not in {a["number"] for a in self.accounts}: return self.async_abort(reason="no_accounts")
            api=Client(async_get_clientsession(self.hass),self.login_data["refresh_token"])
            try:
                await api.login()
                if not await api.meters(account): return self.async_abort(reason="no_smart_meter")
            except (ApiError,AuthError): return self.async_abort(reason="cannot_connect")
            self.login_data["refresh_token"]=api.refresh_token
            data={**self.login_data,"account":account}
            if self.source == config_entries.SOURCE_REAUTH:
                return self.async_update_reload_and_abort(self._get_reauth_entry(),data_updates=data)
            await self.async_set_unique_id(account)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"Portsmouth Water {account}",data=data)
        return self.async_show_form(step_id="account",data_schema=vol.Schema({vol.Required("account"):vol.In({a["number"]:a["number"] for a in self.accounts})}))
    async def async_step_reauth(self,entry_data):
        return await self.async_step_user()


class OptionsFlow(config_entries.OptionsFlowWithReload):
    """Choose units and reload the integration when the choice changes."""
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            if user_input.get(CONF_UNIT) not in UNITS:
                return self.async_show_form(step_id="init", data_schema=self._schema(), errors={"base": "invalid_unit"})
            return self.async_create_entry(title="", data={**self.config_entry.options, **user_input})
        return self.async_show_form(step_id="init", data_schema=self._schema())

    def _schema(self):
        return vol.Schema({vol.Required(CONF_UNIT, default=self.config_entry.options.get(CONF_UNIT, DEFAULT_UNIT)): vol.In(UNITS)})
