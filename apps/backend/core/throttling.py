"""Throttling basato sull'IP reale, non sull'header X-Forwarded-For.

DRF, con ``NUM_PROXIES=None``, costruisce la chiave del throttle con l'intero
header ``X-Forwarded-For`` inviato dal client: un attaccante può cambiarlo a
ogni richiesta e aggirare i limiti di login/registrazione. Qui si riusa
``core.net.get_client_ip``, che considera l'header solo se il peer immediato è
un proxy fidato e percorre la catena da destra a sinistra.
"""
from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle

from .net import get_client_ip


class ClientIpScopedRateThrottle(ScopedRateThrottle):
    def get_ident(self, request) -> str:
        address = get_client_ip(request)
        if address is not None:
            return str(address)
        return super().get_ident(request)
