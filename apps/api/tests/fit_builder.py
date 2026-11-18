"""Codificador mínimo de ficheros FIT para generar actividades sintéticas en los tests.

Escribe un `file_id` y un mensaje `record` por muestra (timestamp, FC, cadencia y potencia),
con la cabecera y los CRC del protocolo FIT. `None` se codifica como valor no válido.
"""

import struct
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)
_CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)  # fmt: skip


def fit_crc(data: bytes) -> int:
    crc = 0
    for byte in data:
        for nibble in (byte & 0xF, (byte >> 4) & 0xF):
            tmp = _CRC_TABLE[crc & 0xF]
            crc = (crc >> 4) & 0x0FFF
            crc = crc ^ tmp ^ _CRC_TABLE[nibble]
    return crc


@dataclass(frozen=True)
class Record:
    timestamp: datetime
    power_w: int | None
    heart_rate_bpm: int | None = None
    cadence_rpm: int | None = None


def _definition(local: int, global_num: int, fields: list[tuple[int, int, int]]) -> bytes:
    body = struct.pack("<BBHB", 0, 0, global_num, len(fields))
    for number, size, base_type in fields:
        body += struct.pack("<BBB", number, size, base_type)
    return bytes([0x40 | local]) + body


def build_fit(records: Iterable[Record]) -> bytes:
    data = bytearray()
    # file_id: type (0, enum) = 4 (activity).
    data += _definition(0, 0, [(0, 1, 0x00)])
    data += bytes([0x00, 4])
    # record: timestamp (253, uint32), heart_rate (3, uint8), cadence (4, uint8), power (7, uint16)
    data += _definition(1, 20, [(253, 4, 0x86), (3, 1, 0x02), (4, 1, 0x02), (7, 2, 0x84)])
    for record in records:
        seconds = int((record.timestamp - FIT_EPOCH).total_seconds())
        data += bytes([0x01]) + struct.pack(
            "<IBBH",
            seconds,
            0xFF if record.heart_rate_bpm is None else record.heart_rate_bpm,
            0xFF if record.cadence_rpm is None else record.cadence_rpm,
            0xFFFF if record.power_w is None else record.power_w,
        )
    header = struct.pack("<BBHI4s", 14, 0x20, 2132, len(data), b".FIT")
    header += struct.pack("<H", fit_crc(header))
    body = header + bytes(data)
    return body + struct.pack("<H", fit_crc(body))


def steady_test(
    start: datetime,
    *,
    warmup_s: int = 900,
    warmup_w: int = 150,
    test_s: int = 1200,
    test_w: int = 250,
    cooldown_s: int = 600,
    cooldown_w: int = 120,
    heart_rate: int = 160,
) -> list[Record]:
    """Calentamiento, bloque constante y vuelta a la calma, a 1 Hz."""
    records: list[Record] = []
    offset = 0
    for duration, watts, hr in (
        (warmup_s, warmup_w, heart_rate - 25),
        (test_s, test_w, heart_rate),
        (cooldown_s, cooldown_w, heart_rate - 30),
    ):
        for _ in range(duration):
            records.append(Record(start + timedelta(seconds=offset), watts, hr, 90))
            offset += 1
    return records
