"""Shared meter entity."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
class MeterEntity(CoordinatorEntity):
    _attr_has_entity_name=True
    def __init__(self,coordinator,serial,key,name):
        super().__init__(coordinator)
        self.serial=serial
        self._attr_unique_id=f"{coordinator.entry.data['account']}_{serial}_{key}"
        self._attr_name=name
        self._attr_device_info=DeviceInfo(identifiers={(DOMAIN,f"{coordinator.entry.data['account']}_{serial}")},name=f"Portsmouth Water {serial}",manufacturer="Portsmouth Water",model="Smart water meter")
    @property
    def available(self):
        return super().available and self.serial in (self.coordinator.data or {})
    @property
    def readings(self):
        return self.coordinator.data[self.serial]
    @property
    def latest(self):
        rows=self.readings["daily"]
        return rows[max(rows,key=int)] if rows else None
