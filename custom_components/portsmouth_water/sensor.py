"""Latest daily usage and reading date."""
from datetime import datetime
from homeassistant.components.sensor import SensorEntity,SensorDeviceClass
from homeassistant.const import UnitOfVolume
from .const import DOMAIN
from .entity import MeterEntity
async def async_setup_entry(hass,entry,async_add_entities):
    c=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([cls(c,s) for s in c.data for cls in (DailyUsage,ReadingDate)])
class DailyUsage(MeterEntity,SensorEntity):
    _attr_device_class=SensorDeviceClass.WATER
    _attr_native_unit_of_measurement=UnitOfVolume.LITERS
    _attr_suggested_display_precision=0
    def __init__(self,c,s): super().__init__(c,s,"daily","Latest daily usage")
    @property
    def native_value(self): return float(self.latest["value"])*1000 if self.latest else None
    @property
    def extra_state_attributes(self):
        return {"reading_date":datetime.fromisoformat(self.latest["start"]).date().isoformat() if self.latest else None,"water_dashboard_statistic":self.readings["statistic_id"]}
class ReadingDate(MeterEntity,SensorEntity):
    _attr_device_class=SensorDeviceClass.DATE
    def __init__(self,c,s): super().__init__(c,s,"date","Latest reading date")
    @property
    def native_value(self): return datetime.fromisoformat(self.latest["start"]).date() if self.latest else None
