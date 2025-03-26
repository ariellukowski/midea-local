"""Midea local FA for 560000AG device."""

import json
import logging
from enum import StrEnum
from typing import Any, ClassVar

from midealocal.const import DeviceType, ProtocolVersion
from midealocal.device import MideaDevice

from .message import MessageFA56AGResponse, MessageQuery, MessageSet

_LOGGER = logging.getLogger(__name__)


class DeviceAttributes(StrEnum):
    """Midea FA device attributes."""

    power = "power"
    mode = "mode"
    fan_speed = "fan_speed"
    oscillate = "oscillate"


class MideaFA56AGDevice(MideaDevice):
    """Midea FA device."""

    _modes = {
        "Normal": 0,
        "Sleep": 2,
        "Smart": 12,
        "ION": 13
    }

    def __init__(
        self,
        name: str,
        device_id: int,
        ip_address: str,
        port: int,
        token: str,
        key: str,
        device_protocol: ProtocolVersion,
        model: str,
        subtype: int,
        customize: str,
    ) -> None:
        """Initialize Midea FA device."""
        super().__init__(
            name=name,
            device_id=device_id,
            device_type=DeviceType.FA,
            ip_address=ip_address,
            port=port,
            token=token,
            key=key,
            device_protocol=device_protocol,
            model=model,
            subtype=subtype,
            attributes={
                DeviceAttributes.power: False,
                DeviceAttributes.mode: 0,
                DeviceAttributes.fan_speed: 0,
                DeviceAttributes.oscillate: False,
            },
        )
        self._default_speed_count = 10
        self._speed_count: int = self._default_speed_count
        self.set_customize(customize)

    @property
    def speed_count(self) -> int:
        """Return the speed count of the device."""
        return self._speed_count

    @property
    def preset_modes(self) -> list[str]:
        """Return a list of preset modes."""
        return list(self._modes.keys())

    def build_query(self) -> list[MessageQuery]:
        """Midea FA device build query."""
        return [MessageQuery(self._message_protocol_version)]

    def process_message(self, msg: bytes) -> dict[str, Any]:
        """Midea FA device process message."""
        message = MessageFA56AGResponse(msg)
        _LOGGER.debug("[%s] Received: %s", self.device_id, message)
        new_status = {}
        for status in self._attributes:
            if hasattr(message, str(status)):
                value = getattr(message, str(status))
                if status == DeviceAttributes.mode:
                    self._attributes[status] = next((k for k, v in MideaFA56AGDevice._modes.items() if v == value), None)
                elif status == DeviceAttributes.power:
                    self._attributes[status] = value
                    if not value:
                        self._attributes[DeviceAttributes.fan_speed] = 0
                elif (
                    status == DeviceAttributes.fan_speed
                    and not self._attributes[DeviceAttributes.power]
                ):
                    self._attributes[status] = 0
                else:
                    self._attributes[status] = value
                new_status[str(status)] = self._attributes[status]
        return new_status

    def set_oscillation(self, attr: str, value: int | str | bool) -> MessageSet | None:
        """Set oscillation mode."""
        message: MessageSet | None = None
        if self._attributes[attr] != value:
            if attr == DeviceAttributes.oscillate:
                message = MessageSet(self._message_protocol_version, self.subtype)
                message.oscillate = bool(value)
                if value:
                    message.oscillation_angle = 3  # 90
                    message.oscillation_mode = 1  # Oscillation
        return message

    def set_attribute(self, attr: str, value: bool | int | str) -> None:
        """Set attribute."""
        message = None
        if attr in [
            DeviceAttributes.oscillate
        ]:
            message = self.set_oscillation(attr, value)
        elif (
            attr == DeviceAttributes.fan_speed
            and int(value) > 0
            and not self._attributes[DeviceAttributes.power]
        ):
            message = MessageSet(self._message_protocol_version, self.subtype)
            message.fan_speed = int(value)
            message.power = True
        elif attr == DeviceAttributes.mode:
            if value in MideaFA56AGDevice._modes:
                message = MessageSet(self._message_protocol_version, self.subtype)
                message.mode = MideaFA56AGDevice._modes.get(value)
        elif not (attr == DeviceAttributes.fan_speed and value == 0):
            message = MessageSet(self._message_protocol_version, self.subtype)
            setattr(message, str(attr), value)
        if message is not None:
            self.build_send(message)

    def turn_on(self, fan_speed: int | None = None, mode: str | None = None) -> None:
        """Turn on the device."""
        message = MessageSet(self._message_protocol_version, self.subtype)
        message.power = True
        if fan_speed is not None:
            message.fan_speed = fan_speed
        if mode is None:
            message.mode = mode
        self.build_send(message)

    def set_customize(self, customize: str) -> None:
        """Set customize."""
        self._speed_count = self._default_speed_count
        if customize and len(customize) > 0:
            try:
                params = json.loads(customize)
                if params and "speed_count" in params:
                    self._speed_count = params.get("speed_count")
            except Exception:
                _LOGGER.exception("[%s] Set customize error", self.device_id)
            self.update_all({"speed_count": self._speed_count})


class MideaAppliance(MideaFA56AGDevice):
    """Midea appliance device."""
