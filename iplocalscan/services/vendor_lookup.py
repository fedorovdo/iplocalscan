from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib.resources import files

from ..core.mac import oui_prefix

logger = logging.getLogger(__name__)


class LocalOuiVendorLookup:
    def __init__(self) -> None:
        self._vendor_map = _load_oui_vendor_map()

    def lookup_vendor(self, mac_address: str | None) -> str | None:
        prefix = oui_prefix(mac_address)
        if prefix is None:
            return None

        vendor = self._vendor_map.get(prefix)
        if vendor is None:
            logger.debug(
                "Vendor prefix not found in bundled OUI database.",
                extra={
                    "event": "vendor_lookup_not_found",
                    "oui_prefix": prefix,
                },
            )
            return None

        logger.debug(
            "Resolved vendor from bundled OUI database.",
            extra={
                "event": "vendor_lookup_resolved",
                "oui_prefix": prefix,
                "vendor": vendor,
            },
        )
        return vendor


@lru_cache(maxsize=1)
def _load_oui_vendor_map() -> dict[str, str]:
    resource = files("iplocalscan.services.data").joinpath("oui.json")
    with resource.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    return {str(prefix).upper(): str(vendor) for prefix, vendor in payload.items()}

