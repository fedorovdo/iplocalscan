from __future__ import annotations

import logging
import random
import socket
import threading
from dataclasses import dataclass
from typing import Final

from ..core.entities import DeviceIdentity

logger = logging.getLogger(__name__)

SYS_DESCR_OID: Final[str] = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID_OID: Final[str] = "1.3.6.1.2.1.1.2.0"
SYS_NAME_OID: Final[str] = "1.3.6.1.2.1.1.5.0"
PRINTER_NAME_OID: Final[str] = "1.3.6.1.2.1.43.5.1.1.16.1"
PRINTER_SERIAL_OID: Final[str] = "1.3.6.1.2.1.43.5.1.1.17.1"

_REQUEST_OIDS: Final[tuple[str, ...]] = (
    SYS_DESCR_OID,
    SYS_OBJECT_ID_OID,
    SYS_NAME_OID,
    PRINTER_NAME_OID,
    PRINTER_SERIAL_OID,
)


@dataclass(frozen=True, slots=True)
class _BerValue:
    tag: int
    value: bytes


class LightweightSnmpIdentityService:
    """Minimal SNMP v2c GET client for printer identity fields."""

    def __init__(
        self,
        *,
        community: str = "public",
        port: int = 161,
        timeout_seconds: float = 0.3,
        max_concurrent_queries: int = 16,
    ) -> None:
        self._community = community
        self._port = port
        self._timeout_seconds = timeout_seconds
        self._semaphore = threading.BoundedSemaphore(max(1, max_concurrent_queries))

    def query_identity(self, ip_address: str) -> DeviceIdentity | None:
        request_id = random.randint(1, 2_147_483_647)
        request = _build_get_request(
            request_id=request_id,
            community=self._community,
            oids=_REQUEST_OIDS,
        )

        acquired = self._semaphore.acquire(timeout=self._timeout_seconds)
        if not acquired:
            logger.debug(
                "SNMP identity query skipped because concurrency limit was reached.",
                extra={
                    "event": "snmp_identity_concurrency_limited",
                    "ip_address": ip_address,
                },
            )
            return None

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as snmp_socket:
                snmp_socket.settimeout(self._timeout_seconds)
                snmp_socket.sendto(request, (ip_address, self._port))
                response, _ = snmp_socket.recvfrom(8192)
        except (OSError, TimeoutError):
            logger.debug(
                "SNMP identity query did not receive a response.",
                extra={
                    "event": "snmp_identity_no_response",
                    "ip_address": ip_address,
                },
            )
            return None
        finally:
            self._semaphore.release()

        try:
            values = _parse_get_response(response)
        except ValueError:
            logger.debug(
                "SNMP identity response was invalid.",
                extra={
                    "event": "snmp_identity_invalid_response",
                    "ip_address": ip_address,
                },
            )
            return None

        identity = DeviceIdentity(
            device_model=_first_text(
                values.get(PRINTER_NAME_OID),
                values.get(SYS_DESCR_OID),
            ),
            serial_number=_clean_text(values.get(PRINTER_SERIAL_OID)),
            snmp_name=_clean_text(values.get(SYS_NAME_OID)),
            snmp_description=_clean_text(values.get(SYS_DESCR_OID)),
            snmp_object_id=_clean_text(values.get(SYS_OBJECT_ID_OID)),
        )
        if not identity.has_data():
            return None

        logger.debug(
            "Resolved device identity via SNMP.",
            extra={
                "event": "snmp_identity_resolved",
                "ip_address": ip_address,
                "snmp_name": identity.snmp_name,
                "device_model": identity.device_model,
                "serial_number": identity.serial_number,
            },
        )
        return identity


def _build_get_request(
    *,
    request_id: int,
    community: str,
    oids: tuple[str, ...],
) -> bytes:
    varbinds = b"".join(
        _encode_tlv(
            0x30,
            _encode_oid(oid) + _encode_tlv(0x05, b""),
        )
        for oid in oids
    )
    pdu = _encode_tlv(
        0xA0,
        b"".join(
            (
                _encode_integer(request_id),
                _encode_integer(0),
                _encode_integer(0),
                _encode_tlv(0x30, varbinds),
            )
        ),
    )
    return _encode_tlv(
        0x30,
        b"".join(
            (
                _encode_integer(1),
                _encode_tlv(0x04, community.encode("ascii", errors="ignore")),
                pdu,
            )
        ),
    )


def _parse_get_response(payload: bytes) -> dict[str, str]:
    reader = _BerReader(payload)
    message = reader.read_expected(0x30)
    message_reader = _BerReader(message)
    message_reader.read_expected(0x02)
    message_reader.read_expected(0x04)
    pdu = message_reader.read_any()
    if pdu.tag != 0xA2:
        raise ValueError("SNMP response PDU was not GetResponse")

    pdu_reader = _BerReader(pdu.value)
    pdu_reader.read_expected(0x02)
    error_status = _decode_integer_bytes(pdu_reader.read_expected(0x02))
    pdu_reader.read_expected(0x02)
    varbind_list = pdu_reader.read_expected(0x30)
    if error_status != 0:
        return {}

    values: dict[str, str] = {}
    varbind_reader = _BerReader(varbind_list)
    while not varbind_reader.is_done:
        varbind = _BerReader(varbind_reader.read_expected(0x30))
        oid = _decode_oid_bytes(varbind.read_expected(0x06))
        value = varbind.read_any()
        decoded_value = _decode_snmp_value(value)
        if decoded_value:
            values[oid] = decoded_value
    return values


def _decode_snmp_value(value: _BerValue) -> str | None:
    if value.tag == 0x04:
        return value.value.decode("utf-8", errors="replace").strip("\x00\r\n\t ")
    if value.tag == 0x06:
        return _decode_oid_bytes(value.value)
    if value.tag == 0x02:
        return str(_decode_integer_bytes(value.value))
    return None


def _encode_integer(value: int) -> bytes:
    if value == 0:
        encoded = b"\x00"
    else:
        encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
        if encoded[0] & 0x80:
            encoded = b"\x00" + encoded
    return _encode_tlv(0x02, encoded)


def _encode_oid(oid: str) -> bytes:
    parts = [int(part) for part in oid.split(".")]
    if len(parts) < 2:
        raise ValueError("OID must have at least two parts")

    encoded = bytes([parts[0] * 40 + parts[1]])
    for part in parts[2:]:
        encoded += _encode_base128(part)
    return _encode_tlv(0x06, encoded)


def _encode_base128(value: int) -> bytes:
    if value == 0:
        return b"\x00"

    chunks: list[int] = []
    while value:
        chunks.append(value & 0x7F)
        value >>= 7
    chunks.reverse()
    for index in range(len(chunks) - 1):
        chunks[index] |= 0x80
    return bytes(chunks)


def _encode_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _encode_length(len(value)) + value


def _encode_length(length: int) -> bytes:
    if length < 0x80:
        return bytes([length])

    encoded = length.to_bytes((length.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(encoded)]) + encoded


def _decode_integer_bytes(value: bytes) -> int:
    return int.from_bytes(value, "big", signed=bool(value and value[0] & 0x80))


def _decode_oid_bytes(value: bytes) -> str:
    if not value:
        raise ValueError("OID payload is empty")

    first = value[0]
    parts = [first // 40, first % 40]
    index = 1
    while index < len(value):
        sub_identifier = 0
        while True:
            if index >= len(value):
                raise ValueError("OID sub-identifier is incomplete")
            byte = value[index]
            index += 1
            sub_identifier = (sub_identifier << 7) | (byte & 0x7F)
            if not byte & 0x80:
                break
        parts.append(sub_identifier)
    return ".".join(str(part) for part in parts)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = " ".join(value.split())
    return cleaned_value or None


def _first_text(*values: str | None) -> str | None:
    for value in values:
        cleaned_value = _clean_text(value)
        if cleaned_value:
            return cleaned_value
    return None


class _BerReader:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._offset = 0

    @property
    def is_done(self) -> bool:
        return self._offset >= len(self._payload)

    def read_expected(self, expected_tag: int) -> bytes:
        value = self.read_any()
        if value.tag != expected_tag:
            raise ValueError("Unexpected BER tag")
        return value.value

    def read_any(self) -> _BerValue:
        if self._offset >= len(self._payload):
            raise ValueError("Unexpected end of BER payload")

        tag = self._payload[self._offset]
        self._offset += 1
        length = self._read_length()
        end_offset = self._offset + length
        if end_offset > len(self._payload):
            raise ValueError("BER value length exceeds payload")

        value = self._payload[self._offset:end_offset]
        self._offset = end_offset
        return _BerValue(tag=tag, value=value)

    def _read_length(self) -> int:
        if self._offset >= len(self._payload):
            raise ValueError("Missing BER length")

        first = self._payload[self._offset]
        self._offset += 1
        if not first & 0x80:
            return first

        length_size = first & 0x7F
        if length_size == 0 or length_size > 4:
            raise ValueError("Unsupported BER length")

        end_offset = self._offset + length_size
        if end_offset > len(self._payload):
            raise ValueError("Incomplete BER length")

        length = int.from_bytes(self._payload[self._offset:end_offset], "big")
        self._offset = end_offset
        return length
