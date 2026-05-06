from __future__ import annotations

import logging
import re
import socket
import subprocess
import sys
import time
from collections.abc import Sequence

from ..core.mac import normalize_mac_address

logger = logging.getLogger(__name__)

_ARP_ENTRY_PATTERN = re.compile(
    r"^\s*(?P<ip>\d+\.\d+\.\d+\.\d+)\s+"
    r"(?P<mac>(?:[0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2})\s+"
    r"(?P<entry_type>\S+)\s*$"
)
_IP_MAC_LINE_PATTERN = re.compile(
    r"(?P<ip>\d+\.\d+\.\d+\.\d+).*?"
    r"(?P<mac>(?:[0-9a-fA-F]{2}[-:]){5}[0-9a-fA-F]{2})"
)
_NBTSTAT_NAME_PATTERN = re.compile(
    r"^\s*(?P<name>[^\s<].*?)\s+<(?P<suffix>[0-9A-Fa-f]{2})>\s+"
    r"(?P<entry_type>UNIQUE|GROUP)\s+(?P<status>\w+)\s*$"
)


class ReverseDnsHostnameResolver:
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
            "Resolved hostname via reverse DNS.",
            extra={
                "event": "reverse_dns_resolved",
                "ip_address": ip_address,
                "hostname": hostname,
            },
        )
        return hostname


class WindowsNetbiosHostnameResolver:
    def __init__(self, *, timeout_seconds: float = 1.0) -> None:
        self._timeout_seconds = timeout_seconds

    def resolve_hostname(self, ip_address: str) -> str | None:
        if not sys.platform.startswith("win"):
            return None

        try:
            completed_process = _run_command(
                ["nbtstat", "-A", ip_address],
                capture_output=True,
                text=True,
                errors="ignore",
                timeout=self._timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.debug(
                "NetBIOS hostname lookup failed to execute.",
                extra={
                    "event": "netbios_lookup_failed",
                    "ip_address": ip_address,
                },
            )
            return None

        if completed_process.returncode != 0:
            logger.debug(
                "NetBIOS hostname lookup returned a non-zero exit code.",
                extra={
                    "event": "netbios_lookup_non_zero_exit",
                    "ip_address": ip_address,
                    "returncode": completed_process.returncode,
                },
            )
            return None

        candidates: list[tuple[int, str]] = []
        for line in completed_process.stdout.splitlines():
            match = _NBTSTAT_NAME_PATTERN.match(line)
            if match is None:
                continue

            entry_type = match.group("entry_type").upper()
            if entry_type != "UNIQUE":
                continue

            suffix = match.group("suffix").upper()
            name = match.group("name").strip()
            if not name or name == "__MSBROWSE__":
                continue

            priority = {"20": 0, "00": 1, "03": 2}.get(suffix, 10)
            candidates.append((priority, name))

        if not candidates:
            logger.debug(
                "NetBIOS hostname lookup found no usable entries.",
                extra={
                    "event": "netbios_lookup_not_found",
                    "ip_address": ip_address,
                },
            )
            return None

        candidates.sort(key=lambda item: item[0])
        hostname = candidates[0][1]
        logger.debug(
            "Resolved hostname via NetBIOS.",
            extra={
                "event": "netbios_lookup_resolved",
                "ip_address": ip_address,
                "hostname": hostname,
            },
        )
        return hostname


class CompositeHostnameResolver:
    def __init__(self, resolvers: Sequence[object]) -> None:
        self._resolvers = tuple(resolvers)

    def resolve_hostname(self, ip_address: str) -> str | None:
        for resolver in self._resolvers:
            hostname = resolver.resolve_hostname(ip_address)
            if hostname:
                return hostname
        return None


class WindowsArpTableMacAddressResolver:
    def __init__(
        self,
        *,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.08,
        ping_timeout_ms: int = 250,
        command_timeout_seconds: float = 1.0,
    ) -> None:
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._ping_timeout_ms = ping_timeout_ms
        self._command_timeout_seconds = command_timeout_seconds

    def resolve_mac_address(self, ip_address: str) -> str | None:
        if not sys.platform.startswith("win"):
            return None

        for attempt in range(1, self._max_attempts + 1):
            self._refresh_arp_neighbor(ip_address)
            time.sleep(self._retry_delay_seconds)

            mac_address = self._lookup_mac_address(ip_address, targeted=True)
            if mac_address is None:
                mac_address = self._lookup_mac_address(ip_address, targeted=False)
            if mac_address is None:
                mac_address = self._lookup_neighbor_cache_mac_address(ip_address)
            if mac_address is not None:
                logger.debug(
                    "Resolved MAC address from Windows neighbor data.",
                    extra={
                        "event": "windows_mac_resolved",
                        "ip_address": ip_address,
                        "mac_address": mac_address,
                        "attempt": attempt,
                    },
                )
                return mac_address

        logger.debug(
            "ARP table did not contain a MAC address after retries.",
            extra={
                "event": "arp_mac_not_found",
                "ip_address": ip_address,
                "attempts": self._max_attempts,
            },
        )
        return None

    def _refresh_arp_neighbor(self, ip_address: str) -> None:
        try:
            _run_command(
                ["ping", "-n", "1", "-w", str(self._ping_timeout_ms), ip_address],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=max(2, round(self._ping_timeout_ms / 1000) + 1),
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.debug(
                "ARP warm-up ping failed.",
                extra={
                    "event": "arp_warmup_failed",
                    "ip_address": ip_address,
                },
            )

    def _lookup_mac_address(self, ip_address: str, *, targeted: bool) -> str | None:
        command = ["arp", "-a", ip_address] if targeted else ["arp", "-a"]
        try:
            completed_process = _run_command(
                command,
                capture_output=True,
                text=True,
                errors="ignore",
                timeout=self._command_timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired):
            logger.debug(
                "Failed to read ARP table.",
                extra={
                    "event": "arp_read_failed",
                    "ip_address": ip_address,
                    "targeted": targeted,
                },
            )
            return None

        if completed_process.returncode != 0:
            logger.debug(
                "ARP command completed with a non-zero exit code.",
                extra={
                    "event": "arp_read_non_zero_exit",
                    "ip_address": ip_address,
                    "targeted": targeted,
                    "returncode": completed_process.returncode,
                },
            )
            return None

        for line in completed_process.stdout.splitlines():
            match = _ARP_ENTRY_PATTERN.match(line)
            if match is None or match.group("ip") != ip_address:
                continue

            return normalize_mac_address(match.group("mac"))

        return None

    def _lookup_neighbor_cache_mac_address(self, ip_address: str) -> str | None:
        for command_name, command in (
            (
                "Get-NetNeighbor",
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "Get-NetNeighbor -AddressFamily IPv4 -IPAddress $args[0] "
                        "| Select-Object -Property IPAddress,LinkLayerAddress,State "
                        "| Format-Table -HideTableHeaders"
                    ),
                    ip_address,
                ],
            ),
            (
                "netsh",
                ["netsh", "interface", "ipv4", "show", "neighbors"],
            ),
        ):
            try:
                completed_process = _run_command(
                    command,
                    capture_output=True,
                    text=True,
                    errors="ignore",
                    timeout=self._command_timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired):
                logger.debug(
                    "Failed to read Windows neighbor cache.",
                    extra={
                        "event": "neighbor_cache_read_failed",
                        "ip_address": ip_address,
                        "command": command_name,
                    },
                )
                continue

            if completed_process.returncode != 0:
                logger.debug(
                    "Windows neighbor cache command returned a non-zero exit code.",
                    extra={
                        "event": "neighbor_cache_non_zero_exit",
                        "ip_address": ip_address,
                        "command": command_name,
                        "returncode": completed_process.returncode,
                    },
                )
                continue

            mac_address = self._parse_ip_mac_lines(
                completed_process.stdout,
                ip_address=ip_address,
            )
            if mac_address is not None:
                logger.debug(
                    "Resolved MAC address from Windows neighbor cache.",
                    extra={
                        "event": "neighbor_cache_mac_resolved",
                        "ip_address": ip_address,
                        "command": command_name,
                        "mac_address": mac_address,
                    },
                )
                return mac_address

        return None

    def _parse_ip_mac_lines(self, output: str, *, ip_address: str) -> str | None:
        for line in output.splitlines():
            match = _IP_MAC_LINE_PATTERN.search(line)
            if match is None or match.group("ip") != ip_address:
                continue

            mac_address = normalize_mac_address(match.group("mac"))
            if mac_address is not None:
                return mac_address

        return None


def _run_command(command: list[str], **kwargs):
    run_kwargs = {"args": command, "check": False}
    run_kwargs.update(kwargs)
    creation_flags = _subprocess_creation_flags()
    if creation_flags:
        run_kwargs["creationflags"] = creation_flags
    return subprocess.run(**run_kwargs)


def _subprocess_creation_flags() -> int:
    if hasattr(subprocess, "CREATE_NO_WINDOW") and sys.platform.startswith("win"):
        return int(subprocess.CREATE_NO_WINDOW)
    return 0
