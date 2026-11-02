"""Client address helpers shared by the setup and authentication flows."""
import ipaddress
from typing import Optional

from django.conf import settings


def _parse(value: Optional[str]):
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _networks(values):
    networks = []
    for value in values:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            continue
    return networks


def _trusted_proxies():
    return _networks(settings.TRUSTED_PROXY_CIDRS)


def _setup_networks():
    return _networks(settings.SETUP_ALLOWED_CIDRS)


def _is_trusted_proxy(address) -> bool:
    return any(address in network for network in _trusted_proxies())


def get_client_ip(request) -> Optional[ipaddress._BaseAddress]:
    """Return the real client address.

    ``X-Forwarded-For`` is only used when the immediate peer is a trusted
    proxy. The chain is walked from right to left so a client cannot spoof an
    allowed address by prepending a fake header: the proxy appends the real
    peer after anything the client sent.
    """
    remote = _parse(request.META.get("REMOTE_ADDR"))
    if remote is None:
        return None
    if not _is_trusted_proxy(remote):
        return remote

    chain = []
    for candidate in request.META.get("HTTP_X_FORWARDED_FOR", "").split(","):
        address = _parse(candidate)
        if address is not None:
            chain.append(address)
    if not chain:
        return remote

    chain.append(remote)
    for address in reversed(chain):
        if not _is_trusted_proxy(address):
            return address
    # Every hop is a trusted proxy: the left-most value is the origin.
    return chain[0]


def is_setup_address_allowed(address) -> bool:
    """Setup is allowed only from localhost and Tailscale, per DC-052."""
    if address is None:
        return False
    return any(address in network for network in _setup_networks())
