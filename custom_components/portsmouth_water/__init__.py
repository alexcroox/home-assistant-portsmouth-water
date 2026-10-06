"""Portsmouth Water consumption and historical statistics."""
from datetime import timedelta
import logging
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_add_external_statistics, async_update_statistics_metadata
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import Client, AuthError, ApiError
from .const import DOMAIN, PLATFORMS, CONF_UNIT, DEFAULT_UNIT
from .data import normalize, cumulative

_LOGGER=logging.getLogger(__name__)
class Coordinator(DataUpdateCoordinator):
    def __init__(self,hass,entry):
        super().__init__(hass,_LOGGER,name="Portsmouth Water",update_interval=timedelta(hours=6),config_entry=entry)
        self.entry=entry
        self.api=Client(async_get_clientsession(hass),entry.data["refresh_token"])
        self.store=Store(hass,1,f"{DOMAIN}.{entry.entry_id}.readings")
        self.history={}
        self.unit=entry.options.get(CONF_UNIT, DEFAULT_UNIT)
    async def _async_update_data(self):
        try:
            await self.api.login()
            if self.api.refresh_token != self.entry.data["refresh_token"]:
                self.hass.config_entries.async_update_entry(self.entry,data={**self.entry.data,"refresh_token":self.api.refresh_token})
            meters=await self.api.meters(self.entry.data["account"])
            if not meters: raise ApiError("No active smart meter")
            result={}
            for meter in meters:
                serial=meter["serialNumber"]
                daily=normalize(await self.api.readings(self.entry.data["account"],meter,"DAY_INTERVAL"))
                history=self.history.setdefault(serial,{})
                history.update(daily)
                rows=cumulative(history, self.unit)
                statistic_id=f"{DOMAIN}:{slugify(self.entry.data['account'] + '_' + serial + '_usage')}"
                if rows:
                    # Canonical history is kept in cubic metres; rewrite all retained
                    # statistics in the selected unit after updating their metadata.
                    async_update_statistics_metadata(self.hass, statistic_id, new_unit_class="volume", new_unit_of_measurement=self.unit)
                    async_add_external_statistics(self.hass,{"mean_type":StatisticMeanType.NONE,"has_sum":True,"name":f"Portsmouth Water {serial} usage","source":DOMAIN,"statistic_id":statistic_id,"unit_class":"volume","unit_of_measurement":self.unit},rows)
                result[serial]={"meter":meter,"daily":daily,"statistic_id":statistic_id}
            await self.store.async_save(self.history)
            return result
        except AuthError as err:
            raise ConfigEntryAuthFailed("Please sign in to Portsmouth Water again") from err
        except (ApiError,ValueError,KeyError) as err:
            raise UpdateFailed(str(err)) from err

async def async_setup_entry(hass,entry):
    coordinator=Coordinator(hass,entry)
    coordinator.history=await coordinator.store.async_load() or {}
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN,{})[entry.entry_id]=coordinator
    await hass.config_entries.async_forward_entry_setups(entry,PLATFORMS)
    return True
async def async_unload_entry(hass,entry):
    if await hass.config_entries.async_unload_platforms(entry,PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
