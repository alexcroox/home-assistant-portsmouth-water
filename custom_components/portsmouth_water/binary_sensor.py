"""Potential leak on the latest complete daily reading."""
from homeassistant.components.binary_sensor import BinarySensorEntity,BinarySensorDeviceClass
from .const import DOMAIN
from .entity import MeterEntity
async def async_setup_entry(hass,entry,async_add_entities):
    c=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Leak(c,s) for s in c.data])
class Leak(MeterEntity,BinarySensorEntity):
    _attr_device_class=BinarySensorDeviceClass.PROBLEM
    def __init__(self,c,s): super().__init__(c,s,"leak","Potential leak")
    @property
    def is_on(self): return self.latest["leak"] if self.latest else None
