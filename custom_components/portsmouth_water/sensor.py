"""Latest daily usage and reading date."""
from datetime import datetime
from homeassistant.components.sensor import SensorEntity,SensorDeviceClass
from homeassistant.helpers import entity_registry as er
from .const import DOMAIN
from .entity import MeterEntity
from .data import usage_value
async def async_setup_entry(hass,entry,async_add_entities):
    c=hass.data[DOMAIN][entry.entry_id]
    registry=er.async_get(hass)
    for serial in c.data:
        unique_id=f"{entry.data['account']}_{serial}_daily"
        entity_id=registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id and (entity := registry.async_get(entity_id)):
            # Refresh the integration suggestion; explicit sensor display-unit
            # overrides remain in the separate sensor options and take priority.
            private_options=dict(entity.options.get("sensor.private", {}))
            private_options["suggested_unit_of_measurement"]=c.unit
            registry.async_update_entity_options(entity_id, "sensor.private", private_options)
    async_add_entities([cls(c,s) for s in c.data for cls in (DailyUsage,ReadingDate)])
class DailyUsage(MeterEntity,SensorEntity):
    _attr_device_class=SensorDeviceClass.WATER
    def __init__(self,c,s):
        super().__init__(c,s,"daily","Latest daily usage")
        self._attr_native_unit_of_measurement=c.unit
        self._attr_suggested_unit_of_measurement=c.unit
        self._attr_suggested_display_precision=0 if c.unit == "L" else 3
    @property
    def native_value(self): return usage_value(self.latest["value"], self.coordinator.unit) if self.latest else None
    @property
    def extra_state_attributes(self):
        return {"reading_date":datetime.fromisoformat(self.latest["start"]).date().isoformat() if self.latest else None,"water_dashboard_statistic":self.readings["statistic_id"]}
class ReadingDate(MeterEntity,SensorEntity):
    _attr_device_class=SensorDeviceClass.DATE
    def __init__(self,c,s): super().__init__(c,s,"date","Latest reading date")
    @property
    def native_value(self): return datetime.fromisoformat(self.latest["start"]).date() if self.latest else None
