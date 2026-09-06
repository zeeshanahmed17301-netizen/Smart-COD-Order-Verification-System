"""Canonical order facts derived from mixed source data."""

from __future__ import annotations

from apps.customers.normalization import normalize_phone

from .source_ip import IP_NOTE_ATTRIBUTE_NAMES, resolve_order_ip


NOTE_ATTRIBUTE_KEY_ALIASES = {
    "first name": "first_name",
    "firstname": "first_name",
    "last name": "last_name",
    "lastname": "last_name",
    "phone": "phone",
    "phone number": "phone",
    "mobile": "phone",
    "mobile number": "phone",
    "email": "email",
    "address": "address1",
    "address 1": "address1",
    "address1": "address1",
    "address 2": "address2",
    "address2": "address2",
    "city": "city",
    "province": "province",
    "state": "province",
    "country": "country",
    "zip": "zip",
    "postal code": "zip",
}

NON_IMPORTANT_ATTRIBUTE_KEYS = {
    "subscribe",
    "subscribe to stay updated with new products and offers!",
    "marketing",
}


def _coalesce(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _clean_text(value) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _build_person_name(data: dict | None) -> str | None:
    if not data:
        return None
    first_name = _clean_text(data.get("first_name"))
    last_name = _clean_text(data.get("last_name"))
    name = " ".join(part for part in [first_name, last_name] if part)
    return name or None


def _normalize_note_attribute_key(value) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    key = text.lower()
    return NOTE_ATTRIBUTE_KEY_ALIASES.get(key, key)


def _build_note_attribute_map(note_attributes) -> dict[str, str]:
    attribute_map: dict[str, str] = {}
    for attribute in note_attributes or []:
        key = _normalize_note_attribute_key((attribute or {}).get("name"))
        value = _clean_text((attribute or {}).get("value"))
        if key and value and key not in attribute_map:
            attribute_map[key] = value
    return attribute_map


def _build_important_note_attributes(note_attributes) -> list[dict]:
    important_attributes: list[dict] = []
    for attribute in note_attributes or []:
        raw_name = _clean_text((attribute or {}).get("name"))
        raw_value = _clean_text((attribute or {}).get("value"))
        normalized_key = _normalize_note_attribute_key(raw_name)
        if not raw_name or not raw_value or not normalized_key:
            continue
        if normalized_key in NON_IMPORTANT_ATTRIBUTE_KEYS or normalized_key in IP_NOTE_ATTRIBUTE_NAMES:
            continue
        important_attributes.append(
            {
                "name": raw_name,
                "value": raw_value,
                "key": normalized_key,
            }
        )
    return important_attributes


def _build_order_address(raw_address: dict | None, note_map: dict[str, str], fallback_address=None) -> dict | None:
    raw_address = raw_address or {}
    address = {
        "name": _coalesce(
            _build_person_name(raw_address),
            " ".join(part for part in [_clean_text(note_map.get("first_name")), _clean_text(note_map.get("last_name"))] if part) or None,
        ),
        "phone": _coalesce(raw_address.get("phone"), note_map.get("phone")),
        "company": _clean_text(raw_address.get("company")),
        "address1": _coalesce(raw_address.get("address1"), note_map.get("address1")),
        "address2": _coalesce(raw_address.get("address2"), note_map.get("address2")),
        "city": _coalesce(raw_address.get("city"), note_map.get("city"), getattr(fallback_address, "city", None)),
        "province": _coalesce(raw_address.get("province"), note_map.get("province"), getattr(fallback_address, "province", None)),
        "country": _coalesce(raw_address.get("country"), note_map.get("country")),
        "zip": _coalesce(raw_address.get("zip"), note_map.get("zip"), getattr(fallback_address, "postal_code", None)),
    }
    lines = [
        address["name"],
        address["address1"],
        address["address2"],
        address["city"],
        address["province"],
        address["country"],
        address["zip"],
    ]
    address["formatted"] = ", ".join(str(line).strip() for line in lines if line) or None
    if not any(value for key, value in address.items() if key != "formatted"):
        return None
    return address


def build_canonical_order_facts(order, snapshot) -> dict | None:
    raw = (snapshot.raw_order_payload or {}) if snapshot else {}
    customer_data = raw.get("customer") or {}
    shipping_address = raw.get("shipping_address") or {}
    billing_address = raw.get("billing_address") or {}
    note_attributes = raw.get("note_attributes") or []
    note_map = _build_note_attribute_map(note_attributes)
    order_ip = resolve_order_ip(
        client_ip=getattr(snapshot, "client_ip", None),
        browser_ip=getattr(snapshot, "browser_ip", None),
        raw_order_payload=raw,
    )

    canonical_shipping = _build_order_address(shipping_address, note_map, order.address)
    canonical_billing = _build_order_address(billing_address, note_map, order.address)

    if not canonical_billing and getattr(snapshot, "billing_matches_shipping", None):
        canonical_billing = canonical_shipping

    return {
        "customer": {
            "name": _coalesce(
                _build_person_name(customer_data),
                _build_person_name(shipping_address),
                " ".join(part for part in [_clean_text(note_map.get("first_name")), _clean_text(note_map.get("last_name"))] if part) or None,
                order.customer.name,
            ),
            "phone": _coalesce(
                normalize_phone(customer_data.get("phone")),
                normalize_phone(raw.get("phone")),
                normalize_phone(shipping_address.get("phone")),
                normalize_phone(billing_address.get("phone")),
                normalize_phone(note_map.get("phone")),
                order.customer.normalized_phone,
                order.customer.phone,
            ),
            "email": _coalesce(
                raw.get("contact_email"),
                raw.get("email"),
                customer_data.get("email"),
                note_map.get("email"),
                order.customer.email,
            ),
            "order_count": _coalesce(customer_data.get("orders_count"), order.customer.total_orders),
            "is_blacklisted": order.customer.is_blacklisted,
            "blacklist_reason": _clean_text(order.customer.blacklist_reason),
        },
        "source": {
            "name": _coalesce(getattr(snapshot, "source_name", None), raw.get("source_name"), order.campaign, order.source),
            "identifier": _coalesce(getattr(snapshot, "source_identifier", None), raw.get("source_identifier")),
            "registered_source_url": _coalesce(getattr(snapshot, "registered_source_url", None)),
        },
        "addresses": {
            "billing_matches_shipping": getattr(snapshot, "billing_matches_shipping", None),
            "shipping_address": canonical_shipping,
            "billing_address": canonical_billing,
            "city": _coalesce(
                (canonical_shipping or {}).get("city"),
                (canonical_billing or {}).get("city"),
                order.customer.city,
                getattr(order.address, "city", None),
            ),
            "province": _coalesce(
                (canonical_shipping or {}).get("province"),
                (canonical_billing or {}).get("province"),
                getattr(order.address, "province", None),
            ),
        },
        "journey": {
            "customer_journey_ready": getattr(snapshot, "customer_journey_ready", False),
            "customer_order_index": getattr(snapshot, "customer_order_index", None),
            "days_to_conversion": getattr(snapshot, "days_to_conversion", None),
        },
        "risk": {
            "shopify_recommendation": _clean_text(getattr(snapshot, "shopify_risk_recommendation", None)),
            "shopify_risk_level": _clean_text(getattr(snapshot, "shopify_risk_level", None)),
        },
        "notes": {
            "customer_note": _coalesce(raw.get("note")),
            "important_attributes": _build_important_note_attributes(note_attributes),
        },
        "network": {
            "order_ip": order_ip["value"],
            "order_ip_source": order_ip["source"],
        },
    }
