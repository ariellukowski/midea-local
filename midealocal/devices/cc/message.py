"""Midea local CC message."""

from enum import IntEnum

from midealocal.const import DeviceType
from midealocal.message import (
    ListTypes,
    MessageBody,
    MessageRequest,
    MessageResponse,
    MessageType,
)


class CCHeatStatus(IntEnum):
    """CC Heat Status."""

    X10 = 1
    X20 = 2


class MessageCCBase(MessageRequest):
    """CC message base."""

    def __init__(
        self,
        protocol_version: int,
        message_type: MessageType,
        body_type: ListTypes,
    ) -> None:
        """Initialize CC message base."""
        super().__init__(
            device_type=DeviceType.CC,
            protocol_version=protocol_version,
            message_type=message_type,
            body_type=body_type,
        )

    @property
    def _body(self) -> bytearray:
        raise NotImplementedError


class MessageQuery(MessageCCBase):
    """CC message query."""

    def __init__(self, protocol_version: int) -> None:
        """Initialize CC message query."""
        super().__init__(
            protocol_version=protocol_version,
            message_type=MessageType.query,
            body_type=ListTypes.X01,
        )

    @property
    def _body(self) -> bytearray:
        return bytearray([0x00] * 23)


class MessageSet(MessageCCBase):
    """CC message set."""

    def __init__(self, protocol_version: int) -> None:
        """Initialize CC message set."""
        super().__init__(
            protocol_version=protocol_version,
            message_type=MessageType.set,
            body_type=ListTypes.C3,
        )
        self.power = False
        self.mode = 4
        self.fan_speed = 0x80
        self.target_temperature: float = 26
        self.eco_mode = False
        self.sleep_mode = False
        self.night_light = False
        self.ventilation = False
        self.aux_heat_status = 0
        self.auto_aux_heat_running = False
        self.swing = False

    @property
    def _body(self) -> bytearray:
        # Byte1, Power Mode
        power = 0x80 if self.power else 0
        mode = 1 << (self.mode - 1)
        # Byte2 fan_speed
        fan_speed = self.fan_speed
        # Byte3 Integer of target_temperature
        temperature_integer = int(self.target_temperature) & 0xFF
        # Byte6 eco_mode ventilation aux_heating
        eco_mode = 0x01 if self.eco_mode else 0
        if self.aux_heat_status == CCHeatStatus.X10:
            aux_heating = 0x10
        elif self.aux_heat_status == CCHeatStatus.X20:
            aux_heating = 0x20
        else:
            aux_heating = 0
        swing = 0x04 if self.swing else 0
        ventilation = 0x08 if self.ventilation else 0
        # Byte8 sleep_mode night_light
        sleep_mode = 0x10 if self.sleep_mode else 0
        night_light = 0x08 if self.night_light else 0
        # Byte11 Dot of target_temperature
        temperature_dot = (
            int((self.target_temperature - temperature_integer) * 10) & 0xFF
        )
        return bytearray(
            [
                power | mode,
                fan_speed,
                temperature_integer,
                # timer
                0x00,
                0x00,
                eco_mode | ventilation | swing | aux_heating,
                # non-stepless fan speed
                0xFF,
                sleep_mode | night_light,
                0x00,
                0x00,
                temperature_dot,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
            ],
        )


class CCGeneralMessageBody(MessageBody):
    """CC message general body."""

    def __init__(self, body: bytearray) -> None:
        """Initialize CC message general body."""
        super().__init__(body)
        self.power = (body[1] & 0x80) > 0
        mode: float = body[1] & 0x1F
        self.mode = 0
        while mode >= 1:
            mode /= 2
            self.mode += 1
        self.fan_speed = body[2]
        self.target_temperature = body[3] + body[19] / 10
        self.indoor_temperature = (body[4] - 40) / 2
        self.eco_mode = (body[13] & 0x01) > 0
        self.sleep_mode = (body[14] & 0x10) > 0
        self.night_light = (body[14] & 0x08) > 0
        self.ventilation = (body[13] & 0x08) > 0
        self.aux_heat_status = (body[14] & 0x60) >> 5
        self.auto_aux_heat_running = (body[13] & 0x02) > 0
        self.fan_speed_level = (body[13] & 0x40) > 0
        self.temperature_precision = 1 if (body[14] & 0x80) > 0 else 0.5
        self.swing = (body[13] & 0x04) > 0
        self.temp_fahrenheit = (body[20] & 0x80) > 0


class MessageCCResponse(MessageResponse):
    """CC message response."""

    def __init__(self, message: bytes) -> None:
        """Initialize CC message response."""
        super().__init__(bytearray(message))
        if (
            (self.message_type == MessageType.query and self.body_type == ListTypes.X01)
            or (
                self.message_type in [MessageType.notify1, MessageType.notify2]
                and self.body_type == ListTypes.X01
            )
            or (self.message_type == MessageType.set and self.body_type == ListTypes.C3)
        ):
            self.set_body(CCGeneralMessageBody(super().body))
        self.set_attr()
