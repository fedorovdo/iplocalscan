from __future__ import annotations

from ipaddress import ip_network


def normalize_network_range(network_range: str) -> str:
    cleaned_value = network_range.strip()
    if not cleaned_value:
        raise ValueError("Network range is required.")

    network = ip_network(cleaned_value, strict=False)
    if network.version != 4:
        raise ValueError("Only IPv4 networks are supported in the first iteration.")

    return network.with_prefixlen

