"""Store integration helpers."""


def is_order_cancelled_at_source(platform: str, order_data: dict) -> bool:
    """Return True if the upstream platform marks the order as cancelled."""
    normalized_platform = (platform or "").strip().lower()
    if normalized_platform == "shopify":
        return bool(order_data.get("cancelled_at") or order_data.get("cancel_reason"))
    return False
