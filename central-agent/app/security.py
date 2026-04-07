from __future__ import annotations

from typing import Any


DENIED_INTEL_FIELDS = {
    "pcap",
    "pcapbase64",
    "pcapbytes",
    "pcapfile",
    "rawpcap",
    "payload",
    "payloadbase64",
    "payloadbytes",
    "payloadhex",
    "rawpayload",
    "rawpayloadhex",
    "flowtext",
    "packetbytes",
    "packethex",
    "rawpackets",
    "rawpacket",
    "applicationpayload",
    "fulll7content",
}


def normalize_field_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def validate_structured_intel(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = normalize_field_name(str(key))
            if normalized in DENIED_INTEL_FIELDS:
                raise ValueError(
                    f"Field `{path}.{key}` is not allowed. Raw pcap or payload-like fields must not be uploaded."
                )
            validate_structured_intel(nested, f"{path}.{key}")
        return

    if isinstance(value, list):
        for index, nested in enumerate(value):
            validate_structured_intel(nested, f"{path}[{index}]")
        return

    if value is None or isinstance(value, (str, int, float, bool)):
        return

    raise ValueError(
        f"Field `{path}` must be structured JSON data composed of objects, arrays, strings, numbers, booleans, or null."
    )
