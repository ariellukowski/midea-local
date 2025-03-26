"""Midea local FA message."""

from midealocal.const import DeviceType
from midealocal.message import (
    ListTypes,
    MessageBody,
    MessageRequest,
    MessageResponse,
    MessageType,
)

MAX_FAN_SPEED = 26
TILTING_ANGLE_GET_BYTE = 25
TILTING_ANGLE_SET_BYTE = 24


class MessageFA56AGBase(MessageRequest):
    """FA message base."""

    def __init__(
        self,
        protocol_version: int,
        message_type: MessageType,
        body_type: ListTypes = ListTypes.X00,
    ) -> None:
        """Initialize the message with protocol version, message type, and body type."""
        super().__init__(
            device_type=DeviceType.FA,
            protocol_version=protocol_version,
            message_type=message_type,
            body_type=body_type,
        )

    @property
    def _body(self) -> bytearray:
        raise NotImplementedError


class MessageQuery(MessageFA56AGBase):
    """Message query."""

    def __init__(self, protocol_version: int) -> None:
        """Initialize the message with protocol version."""
        super().__init__(
            protocol_version=protocol_version,
            message_type=MessageType.query,
        )

    @property
    def body(self) -> bytearray:
        """Return an empty bytearray."""
        return bytearray([])

    @property
    def _body(self) -> bytearray:
        return bytearray([])


class MessageSet(MessageFA56AGBase):
    """Message set."""

    def __init__(self, protocol_version: int, subtype: int) -> None:
        """Initialize the message with protocol version and subtype."""
        super().__init__(
            protocol_version=protocol_version,
            message_type=MessageType.set,
            body_type=ListTypes.X00,
        )
        self._subtype = subtype
        self.power: bool | None = None
        self.mode: int | None = None
        self.fan_speed: int | None = None
        self.oscillate: bool | None = None

    @property
    def _body(self) -> bytearray:
        if 1 <= self._subtype <= ListTypes.X0A or self._subtype == ListTypes.A1:
            _body_return = bytearray(
                [
                    0x00,
                    0x00,
                    0x00,
                    0x80,
                    0x00,
                    0x00,
                    0x00,
                    0x80,
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
            if self._subtype != ListTypes.X0A:
                _body_return[13] = 0xFF
        else:
            _body_return = bytearray(
                [
                    0x00,
                    0x00,
                    0x00,
                    0x80,
                    0x00,
                    0x00,
                    0x00,
                    0x80,
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
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                ],
            )
        if self.power is not None:
            if self.power:
                _body_return[3] = 1
            else:
                _body_return[3] = 0
        if self.mode is not None:
            _body_return[3] = 1 | (((self.mode + 1) << 1) & 0x1E)
        if self.fan_speed is not None and 1 <= self.fan_speed <= MAX_FAN_SPEED:
            _body_return[4] = self.fan_speed
        if self.oscillate is not None:
            if self.oscillate:
                _body_return[7] = 1
            else:
                _body_return[7] = 0
        return _body_return


class FA56AGGeneralMessageBody(MessageBody):
    """General message body."""

    def __init__(self, body: bytearray) -> None:
        """Initialize the message body."""
        super().__init__(body)
        self.power = (body[4] & 0x01) > 0
        mode = (body[4] & 0x1E) >> 1
        if mode > 0:
            self.mode = mode - 1
        fan_speed = body[5]
        if 1 <= fan_speed <= MAX_FAN_SPEED:
            self.fan_speed = fan_speed
        else:
            self.fan_speed = 0
        self.oscillate = (body[8] & 0x01) > 0
        print(f'body: {body.hex(':')}')


class MessageFA56AGResponse(MessageResponse):
    """FA response message."""

    def __init__(self, message: bytes) -> None:
        """Initialize the message."""
        super().__init__(bytearray(message))
        if self.message_type in [
            MessageType.query,
            MessageType.set,
            MessageType.notify1,
        ]:
            self.set_body(FA56AGGeneralMessageBody(super().body))
        self.set_attr()
