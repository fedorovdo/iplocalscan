from __future__ import annotations


def normalize_mac_address(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    hex_value = "".join(character for character in raw_value if character.isalnum()).upper()
    if len(hex_value) != 12:
        return None
    if hex_value in {"000000000000", "FFFFFFFFFFFF"}:
        return None

    return ":".join(hex_value[index : index + 2] for index in range(0, 12, 2))


def oui_prefix(mac_address: str | None) -> str | None:
    normalized_mac = normalize_mac_address(mac_address)
    if normalized_mac is None:
        return None

    return normalized_mac.replace(":", "")[:6]

