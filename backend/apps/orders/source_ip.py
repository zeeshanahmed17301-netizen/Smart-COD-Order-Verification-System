"""Canonical order IP resolution helpers."""

from __future__ import annotations

import ipaddress


IP_NOTE_ATTRIBUTE_NAMES = {
    "ip",
    "ip address",
    "client ip",
    "browser ip",
    "order ip",
}


def normalize_ip(value) -> str | None:
    """Return a valid normalized IP string or None."""
    if value in (None, ""):
        return None

    try:
        return str(ipaddress.ip_address(str(value).strip()))
    except ValueError:
        return None


def extract_note_attribute_ip(note_attributes) -> str | None:
    """Extract an IP-like value from note attributes when present."""
    for attribute in note_attributes or []:
        name = str((attribute or {}).get("name") or "").strip().lower()
        if name not in IP_NOTE_ATTRIBUTE_NAMES:
            continue

        ip_value = normalize_ip((attribute or {}).get("value"))
        if ip_value:
            return ip_value

    return None


def resolve_order_ip(*, client_ip=None, browser_ip=None, raw_order_payload=None) -> dict:
    """Resolve one canonical order IP plus the source it came from."""
    raw = raw_order_payload or {}
    client_details = raw.get("client_details") or {}
    note_attribute_ip = extract_note_attribute_ip(raw.get("note_attributes") or [])

    candidates = [
        ("client_ip", client_ip),
        ("raw_browser_ip", raw.get("browser_ip")),
        ("browser_ip", browser_ip),
        ("client_details_browser_ip", client_details.get("browser_ip")),
        ("note_attribute_ip", note_attribute_ip),
    ]

    for source, candidate in candidates:
        normalized = normalize_ip(candidate)
        if normalized:
            return {
                "value": normalized,
                "source": source,
            }

    return {
        "value": None,
        "source": None,
    }
