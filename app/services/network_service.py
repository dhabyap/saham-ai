import platform
import subprocess
import re
import socket
import logging
import asyncio
import concurrent.futures
from ipaddress import IPv4Network, AddressValueError

logger = logging.getLogger(__name__)


def get_network_base() -> str:
    """Get local network base IP (e.g., 192.168.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return '.'.join(ip.split('.')[:-1])
    except Exception:
        return "192.168.1"


def ping_ip(ip: str) -> bool:
    """Ping a single IP, return True if reachable."""
    param = "-n 1 -w 200" if platform.system().lower() == "windows" else "-c 1 -W1"
    try:
        ret = subprocess.run(
            f"ping {param} {ip}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        return ret.returncode == 0
    except subprocess.TimeoutExpired:
        return False


def scan_arp_cache() -> list[dict]:
    """Parse `arp -a` output for IP + MAC entries."""
    devices = []
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                check=True,
            )

        for line in result.stdout.splitlines():
            line = line.strip()
            # Match IP + MAC pattern: 192.168.1.x xx-xx-xx-xx-xx-xx or xx:xx:xx:xx:xx:xx
            match = re.match(
                r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([\da-fA-F-:]{17})",
                line,
            )
            if match:
                ip = match.group(1)
                mac = match.group(2).replace("-", ":").upper()
                if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                    devices.append({"ip": ip, "mac": mac})
    except Exception as e:
        logger.warning(f"arp -a failed: {e}")

    return devices


def scan_network() -> list[dict]:
    """Scan local network using ARP + ping sweep. No nmap needed."""
    base = get_network_base()
    logger.info(f"Scanning network {base}.0/24 ...")

    # 1. Quick ARP cache read
    arp_devices = scan_arp_cache()
    seen_ips = {d["ip"] for d in arp_devices}

    # 2. Ping sweep common hosts (1-254), but only those NOT already in ARP
    #    Use ThreadPoolExecutor for speed
    to_ping = [f"{base}.{i}" for i in range(1, 255) if f"{base}.{i}" not in seen_ips]

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(ping_ip, to_ping))

    newly_reachable = [
        to_ping[i] for i, reachable in enumerate(results) if reachable
    ]

    # 3. Re-read ARP cache to pick up any new entries from ping
    if newly_reachable:
        import time

        time.sleep(0.5)  # brief wait for ARP to update
        more_arp = scan_arp_cache()
        existing_ips = {d["ip"] for d in arp_devices}
        for d in more_arp:
            if d["ip"] not in existing_ips:
                arp_devices.append(d)
                existing_ips.add(d["ip"])

    # 4. Mark devices without MAC as "alive" from ping
    for ip in newly_reachable:
        if ip not in seen_ips:
            arp_devices.append({"ip": ip, "mac": "N/A"})

    # Deduplicate by IP
    seen = {}
    for d in arp_devices:
        seen[d["ip"]] = d

    result = list(seen.values())
    result.sort(key=lambda x: [int(p) for p in x["ip"].split(".")])
    logger.info(f"Found {len(result)} devices.")
    return result
