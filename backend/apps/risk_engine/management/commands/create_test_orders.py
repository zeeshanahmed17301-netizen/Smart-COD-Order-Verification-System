"""
Management command: create_test_orders
---------------------------------------
Creates synthetic orders that exercise every rule in new-requirement.md,
then rescores each one and prints the results.

Usage:
    python manage.py create_test_orders
    python manage.py create_test_orders --clean   # delete created orders after

Rules exercised
---------------
1. Phone: repeated digits  (03333333333) → fraud high
2. Phone: sequential       (03123456789) → fraud high
3. Phone: same phone >3 orders           → medium risk signal
4. Name: too short / digit in name       → suspicious
5. Name: common valid name (Ali, Fatima) → low-risk trust offset
6. Address: < 10 chars                   → high risk
7. Address: no keyword                   → high risk
8. Address: blacklist word (test/fake)   → high risk
9. Address: vague (near market)          → medium risk
10. Address: good keyword                → low risk
11. Courier: unavailable city            → high RTO
12. Courier: available city              → low RTO
13. History: previous RTO customer       → high fraud+RTO
14. History: good delivery history       → low scores
15. WhatsApp: conv_status=failed         → extra fraud+RTO
16. WhatsApp: conv_status=completed      → no penalty
"""

from __future__ import annotations

import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


# ── helpers ──────────────────────────────────────────────────────────────────

def _uid() -> str:
    return str(uuid.uuid4().int)[:10]


def _make_customer(merchant, name, phone, total_orders=1, delivered=0, rto=0):
    from apps.customers.models import Customer
    cust, _ = Customer.objects.get_or_create(
        merchant=merchant,
        phone=phone,
        defaults=dict(
            name=name,
            total_orders=total_orders,
            delivered_count=delivered,
            rto_count=rto,
        ),
    )
    # Always refresh behavioural counts (in case customer already existed)
    cust.name = name
    cust.total_orders = total_orders
    cust.delivered_count = delivered
    cust.rto_count = rto
    cust.save()
    return cust


def _make_address(customer, full_address, city):
    from apps.addresses.models import Address
    return Address.objects.create(
        customer=customer,
        full_address=full_address,
        city=city,
    )


def _make_order(merchant, customer, address, amount, order_id_suffix):
    from apps.orders.models import Order
    return Order.objects.create(
        order_id=f"TEST_{order_id_suffix}_{_uid()}",
        merchant=merchant,
        customer=customer,
        address=address,
        amount=amount,
        payment_method="cod",
        status="pending",
        source="test",
    )


def _make_conv(order, status):
    """Create a Conversation with the given status to simulate WhatsApp state."""
    from apps.chatbot.models import Conversation
    Conversation.objects.filter(order=order).delete()
    Conversation.objects.create(
        order=order,
        status=status,
        purpose="order_confirmation",
    )


# ── test scenarios ────────────────────────────────────────────────────────────

SCENARIOS = [
    # (label, phone, name, address, city, amount, total_ord, delivered, rto, conv_status, expected_signal)
    (
        "T01 – Repeated-digit phone",
        "03333333333",   # 7× digit '3' → is_suspicious
        "Asim Raza",
        "House 12, Street 5, Block B, Islamabad",
        "Islamabad",
        2500,
        1, 0, 0,
        None,
        "fraud HIGH (phone repeated digit)",
    ),
    (
        "T02 – Sequential phone",
        "03123456789",   # sequential → is_suspicious
        "Asim Raza",
        "House 12, Street 5, Block B, Lahore",
        "Lahore",
        2500,
        1, 0, 0,
        None,
        "fraud HIGH (sequential phone)",
    ),
    (
        "T03 – Same phone >3 orders (repeat customer)",
        "03009999001",
        "Bilal Shah",
        "Flat 3, Block A, Gulshan Colony, Karachi",
        "Karachi",
        3000,
        5, 2, 0,   # 5 total orders → repeat_customer fires
        None,
        "fraud MEDIUM+ (repeat phone)",
    ),
    (
        "T04 – Name too short",
        "03001111001",
        "Az",            # < 3 chars → is_suspicious
        "Plot 4, Phase 2, Defence, Lahore",
        "Lahore",
        1800,
        1, 0, 0,
        None,
        "fraud HIGH (short name)",
    ),
    (
        "T05 – Digit in name",
        "03001111002",
        "Ahmed123",      # digit in name → is_suspicious
        "House 7, Street 3, G-11, Islamabad",
        "Islamabad",
        2200,
        1, 0, 0,
        None,
        "fraud HIGH (digit in name)",
    ),
    (
        "T06 – Common valid name (trust offset)",
        "03001111003",
        "Fatima",        # common name → -5 fraud
        "House 7, Street 3, G-11, Islamabad",
        "Islamabad",
        2200,
        1, 0, 0,
        None,
        "fraud LOW (common name offset)",
    ),
    (
        "T07 – Address too short",
        "03001111004",
        "Kamran Ali",
        "Lahore",        # < 10 chars → high risk
        "Lahore",
        1500,
        1, 0, 0,
        None,
        "fraud HIGH + RTO HIGH (short address)",
    ),
    (
        "T08 – Address no keyword",
        "03001111005",
        "Waqar Hussain",
        "House 5, near the old place, Rawalpindi",  # no valid keyword
        "Rawalpindi",
        1500,
        1, 0, 0,
        None,
        "fraud HIGH (no address keyword)",
    ),
    (
        "T09 – Blacklist word in address",
        "03001111006",
        "Usman Khan",
        "test address, abc area, Faisalabad",   # blacklist: test, abc
        "Faisalabad",
        1500,
        1, 0, 0,
        None,
        "fraud CRITICAL (blacklist word)",
    ),
    (
        "T10 – Vague address (near only)",
        "03001111007",
        "Junaid Malik",
        "near the main market, Multan",   # vague, no structure
        "Multan",
        2000,
        1, 0, 0,
        None,
        "RTO MEDIUM (vague address)",
    ),
    (
        "T11 – Good address + good history",
        "03001111008",
        "Zara Ahmed",
        "House 12, Street 5, Block B, F-8, Islamabad",
        "Islamabad",
        2500,
        4, 4, 0,   # 4 delivered, 0 RTO
        None,
        "fraud LOW + RTO LOW (good profile)",
    ),
    (
        "T12 – Courier unavailable city",
        "03001111009",
        "Naveed Iqbal",
        "Mohalla Gulshan, Main Road, Chitral",
        "Chitral",           # not covered by Leopard/TCS
        2800,
        1, 0, 0,
        None,
        "RTO HIGH (courier unavailable)",
    ),
    (
        "T13 – Previous RTO history",
        "03001111010",
        "Rana Tariq",
        "Plot 3, Sector G, Phase 1, Hayatabad, Peshawar",
        "Peshawar",
        2000,
        3, 0, 2,   # 2 RTOs
        None,
        "fraud HIGH + RTO HIGH (previous RTO)",
    ),
    (
        "T14 – WhatsApp failed conversation",
        "03001111011",
        "Danish Qadir",
        "House 8, Block C, Gulberg, Lahore",
        "Lahore",
        3500,
        1, 0, 0,
        "failed",
        "fraud+RTO bump (WhatsApp failed)",
    ),
    (
        "T15 – WhatsApp completed (confirmed)",
        "03001111012",
        "Sana Butt",
        "House 8, Block C, Gulberg, Lahore",
        "Lahore",
        3500,
        2, 2, 0,
        "completed",
        "fraud LOW (WhatsApp confirmed, good history)",
    ),
    (
        "T16 – High-value COD order",
        "03001111013",
        "Adnan Sheikh",
        "Flat 2, Block 5, Clifton, Karachi",
        "Karachi",
        12000,    # >= 10000 → RTO +8
        1, 0, 0,
        None,
        "RTO MEDIUM+ (high COD amount)",
    ),
]


class Command(BaseCommand):
    help = "Create synthetic test orders covering all new-requirement.md rules and score them."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all TEST_ orders after scoring (useful for CI).",
        )

    def handle(self, *args, **options):
        from apps.risk_engine.services import RiskScoringEngine

        merchant = User.objects.first()
        if not merchant:
            self.stderr.write("No user found. Create a superuser first.")
            return

        created_order_ids = []

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\nCreating test orders (new-requirement.md coverage)\n"
        ))

        rows = []
        for scenario in SCENARIOS:
            (label, phone, name, address_text, city,
             amount, total_ord, delivered, rto, conv_status, expected) = scenario

            try:
                cust = _make_customer(
                    merchant, name, phone,
                    total_orders=total_ord,
                    delivered=delivered,
                    rto=rto,
                )
                addr = _make_address(cust, address_text, city)
                order = _make_order(merchant, cust, addr, amount, label.split()[0])
                created_order_ids.append(order.order_id)

                if conv_status:
                    _make_conv(order, conv_status)

                # Enrich + score
                result = RiskScoringEngine.score_and_save(order)

                order.refresh_from_db()

                rows.append({
                    "label": label,
                    "fraud": order.fraud_score,
                    "rto": order.rto_probability_score,
                    "risk": order.risk_level,
                    "action": order.recommended_action,
                    "expected": expected,
                    "ok": True,
                })
            except Exception as exc:
                rows.append({
                    "label": label,
                    "fraud": "ERR",
                    "rto": "ERR",
                    "risk": "ERR",
                    "action": "ERR",
                    "expected": expected,
                    "ok": False,
                    "error": str(exc),
                })

        # ── Print results table ───────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(
            f"{'Scenario':<42} {'Fraud':>6} {'RTO':>6} {'Risk':<8} {'Action':<18} Expected Signal"
        )
        self.stdout.write("=" * 130)
        for r in rows:
            if r["ok"]:
                line = (
                    f"{r['label']:<42} "
                    f"{r['fraud']:>5.1f}% "
                    f"{r['rto']:>5.1f}% "
                    f"{r['risk']:<8} "
                    f"{r['action']:<18} "
                    f"{r['expected']}"
                )
                if r["risk"] in ("high", "critical"):
                    self.stdout.write(self.style.ERROR(line))
                elif r["risk"] == "medium":
                    self.stdout.write(self.style.WARNING(line))
                else:
                    self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(self.style.ERROR(
                    f"{r['label']:<42} ERROR: {r.get('error','?')[:80]}"
                ))

        self.stdout.write("")

        passed = sum(1 for r in rows if r["ok"])
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"  Scored {passed}/{len(rows)} scenarios successfully."
        ))
        if options.get("clean"):
            from apps.orders.models import Order
            deleted, _ = Order.objects.filter(order_id__in=created_order_ids).delete()
            self.stdout.write(f"  Cleaned up {deleted} test orders.")
