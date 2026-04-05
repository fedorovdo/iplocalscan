from __future__ import annotations

import logging
import re
import socket
import subprocess
import sys

logger = logging.getLogger(__name__)

_ARP_ENTRY_PATTERN = re.compile(
    r"^\s*(?P<ip>\d+\.\d+\.\d+\.\d+)\s+"
    r"(?P<mac>(?:[0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2})\s+"
    r"(?P<entry_type>\S+)\s*$"
)


class SocketHostnameResolver:
    def resolve_hostname(self, ip_address: str) -> str | None:
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
        except (socket.herror, socket.gaierror, OSError):
            logger.debug(
                "Reverse DNS lookup did not return a hostname.",
                extra={
                    "event": "reverse_dns_not_found",
                    "ip_address": ip_address,
                },
            )
            return None

        logger.debug(
            "Resolved hostname.",
            extra={
                "event": "reverse_dns_resolved",
                "ip_address": ip_address,
                "hostname": hostname,
            },
        )
        return hostname


class WindowsArpTableMacAddressResolver:
    def resolve_mac_address(self, ip_address: str) -> str | None:
        if not sys.platform.startswith("win"):
            return None

        try:
            run_kwargs = {
                "args": ["arp", "-a"],
                "capture_output": True,
                "text": True,
                "check": False,
                "errors": "ignore",
            }
            creation_flags = self._subprocess_creation_flags()
            if creation_flags:
                run_kwargs["creationflags"] = creation_flags

            completed_process = subprocess.run(**run_kwargs)
        except OSError:
            logger.exception(
                "Failed to read ARP table.",
                extra={
                    "event": "arp_read_failed",
                    "ip_address": ip_address,
                },
            )
            return None

        if completed_process.returncode != 0:
            logger.warning(
                "ARP command completed with a non-zero exit code.",
                extra={
                    "event": "arp_read_non_zero_exit",
                    "ip_address": ip_address,
                    "returncode": completed_process.returncode,
                },
            )
            return None

        for line in completed_process.stdout.splitlines():
            match = _ARP_ENTRY_PATTERN.match(line)
            if match is None or match.group("ip") != ip_address:
                continue

            normalized_mac = match.group("mac").replace("-", ":").upper()
            logger.debug(
                "Resolved MAC address from ARP table.",
                extra={
                    "event": "arp_mac_resolved",
                    "ip_address": ip_address,
                    "mac_address": normalized_mac,
                },
            )
            return normalized_mac

        logger.debug(
            "ARP table did not contain a MAC address for the host.",
            extra={
                "event": "arp_mac_not_found",
                "ip_address": ip_address,
            },
        )
        return None

    def _subprocess_creation_flags(self) -> int:
        if hasattr(subprocess, "CREATE_NO_WINDOW") and sys.platform.startswith("win"):
            return int(subprocess.CREATE_NO_WINDOW)
        return 0
