from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.addresses.models import Address
from apps.customers.models import Customer
from apps.orders.models import Order, RiskFactor
from apps.risk_engine.services import RULE_ENGINE_VERSION, RiskScoringEngine, ScoreCalibrationService
from apps.risk_engine.validators import (
    validate_address,
    validate_courier,
    validate_name,
    validate_order_history,
    validate_phone,
)

User = get_user_model()


def build_enrichment(**overrides):
    defaults = {
        "enrichment_status": "completed",
        "failure_reason": "",
        "repeat_phone_orders_30d": 0,
        "repeat_phone_orders_3h": 0,
        "repeat_ip_orders_3h": 0,
        "courier_reachable": True,
        "courier_coverage_score": 100.0,
        "is_anonymous": False,
        "is_anonymous_vpn": False,
        "is_public_proxy": False,
        "is_residential_proxy": False,
        "is_tor_exit_node": False,
        "is_hosting_provider": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class RuleValidatorTests(TestCase):
    def test_phone_validator_flags_invalid_and_repetitive_numbers(self):
        valid = validate_phone("03124590876")
        suspicious = validate_phone("03000000000", prior_order_count=4)

        self.assertTrue(valid["valid"])
        self.assertEqual(valid["score_delta"], 2)
        self.assertTrue(suspicious["is_suspicious"])
        self.assertTrue(suspicious["repeat_customer"])
        self.assertIn("repeated_digits", suspicious["flags"])

    def test_name_address_history_and_courier_rules_match_new_policy(self):
        suspicious_name = validate_name("xyz1")
        valid_address = validate_address("House 22, Street 5, G-11", "Islamabad", "G-11")
        weak_address = validate_address("abc near market", "", "")
        reliable_history = validate_order_history(total_orders=4, delivered_count=3, rto_count=0)
        risky_history = validate_order_history(total_orders=4, delivered_count=0, rto_count=2)
        courier_ok = validate_courier(reachable=True, coverage_score=100.0)
        courier_missing = validate_courier(reachable=False, coverage_score=0.0)

        self.assertTrue(suspicious_name["is_suspicious"])
        self.assertTrue(valid_address["is_structured"])
        self.assertTrue(weak_address["has_blacklist_word"])
        self.assertTrue(weak_address["is_vague"])
        self.assertTrue(reliable_history["has_successful_deliveries"])
        self.assertTrue(risky_history["has_previous_rto"])
        self.assertTrue(courier_ok["is_available"])
        self.assertFalse(courier_missing["is_available"])

    def test_address_keyword_and_blacklist_match_on_word_boundaries(self):
        # "test"/"abc" appear only as substrings here — must NOT be blacklisted.
        clean = validate_address(
            "House 12, Greatest Colony, Fabcity Block", "Lahore", "Model Town"
        )
        # Real blacklist words as whole tokens — must be flagged.
        fake = validate_address("abc test house, fake colony", "Lahore", "")

        self.assertFalse(clean["has_blacklist_word"])
        self.assertTrue(clean["has_keyword"])  # "Colony"/"Block" still match
        self.assertTrue(fake["has_blacklist_word"])


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class RiskScoringEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            username="merchant",
            first_name="Merchant",
            last_name="User",
            password="StrongPass123!",
        )

    def create_order(
        self,
        *,
        customer_name="Ali Raza",
        phone="03124590876",
        city="Islamabad",
        full_address="House 22, Street 5, G-11, Islamabad",
        total_orders=3,
        delivered_count=2,
        rto_count=0,
    ):
        customer = Customer.objects.create(
            merchant=self.user,
            name=customer_name,
            phone=phone,
            email="buyer@example.com",
            city=city,
            total_orders=total_orders,
            delivered_count=delivered_count,
            rto_count=rto_count,
        )
        address = Address.objects.create(
            customer=customer,
            full_address=full_address,
            city=city,
            district="G-11" if city else "",
            province="Punjab",
            postal_code="44000" if city else "",
            confidence_score=80,
            status="valid",
        )
        return Order.objects.create(
            order_id=f"ORD-{customer.phone[-4:]}-{Order.objects.count() + 1}",
            merchant=self.user,
            customer=customer,
            address=address,
            amount=Decimal("2500.00"),
            payment_method="cod",
            status="pending",
            chat_status="unverified",
            source="manual",
        )

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_score_and_save_persists_low_risk_order(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        order = self.create_order()
        enrich_mock.return_value = build_enrichment()

        result = RiskScoringEngine.score_and_save(order)
        order.refresh_from_db()

        self.assertEqual(result.risk_level, "low")
        self.assertEqual(result.recommended_action, "ship_order")
        self.assertEqual(order.risk_level, "low")
        self.assertEqual(order.recommended_action, "ship_order")
        self.assertEqual(order.score_calibration_version, RULE_ENGINE_VERSION)
        self.assertEqual(order.score_source, "rules")
        self.assertGreater(RiskFactor.objects.filter(order=order).count(), 0)

    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_calculate_flags_high_risk_order(self, enrich_mock):
        order = self.create_order(
            customer_name="xyz1",
            phone="03000000000",
            city="",
            full_address="abc near market",
            total_orders=4,
            delivered_count=0,
            rto_count=2,
        )
        enrich_mock.return_value = build_enrichment(
            courier_reachable=False,
            courier_coverage_score=0.0,
            is_anonymous_vpn=True,
            repeat_phone_orders_3h=3,
        )

        result = RiskScoringEngine.calculate(order)
        factor_names = {factor["name"] for factor in result.factors}

        self.assertEqual(result.risk_level, "high")
        self.assertEqual(result.recommended_action, "cancel_order")
        self.assertGreaterEqual(result.fraud_score, 60.0)
        self.assertGreaterEqual(result.rto_probability_score, 60.0)
        self.assertIn("Blacklisted Address Terms", factor_names)
        self.assertIn("Previous RTO History", factor_names)
        self.assertIn("Courier Coverage Missing", factor_names)

    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_blacklisted_customer_forces_cancel(self, enrich_mock):
        order = self.create_order()
        order.customer.is_blacklisted = True
        order.customer.blacklist_reason = "Confirmed serial RTO abuser"
        order.customer.save(update_fields=["is_blacklisted", "blacklist_reason"])
        enrich_mock.return_value = build_enrichment()

        result = RiskScoringEngine.calculate(order)
        factor_names = {factor["name"] for factor in result.factors}

        self.assertEqual(result.risk_level, "high")
        self.assertEqual(result.recommended_action, "cancel_order")
        # +40 blacklist, less the -5 common-name ("Ali") trust offset.
        self.assertGreaterEqual(result.fraud_score, 35.0)
        self.assertIn("Blacklisted Customer", factor_names)

    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_ghosting_and_cancellation_history_raise_rto(self, enrich_mock):
        clean = self.create_order(phone="03124590870")
        enrich_mock.return_value = build_enrichment()
        baseline = RiskScoringEngine.calculate(clean)

        repeat_offender = self.create_order(phone="03124590871")
        repeat_offender.customer.ghosted_count = 3
        repeat_offender.customer.cancelled_count = 2
        repeat_offender.customer.save(
            update_fields=["ghosted_count", "cancelled_count"]
        )
        enrich_mock.return_value = build_enrichment()
        result = RiskScoringEngine.calculate(repeat_offender)
        factor_names = {factor["name"] for factor in result.factors}

        self.assertGreater(result.rto_probability_score, baseline.rto_probability_score)
        self.assertIn("Repeated Non-Response", factor_names)
        self.assertIn("Frequent Cancellations", factor_names)

    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_multiple_names_on_same_number_flag_fraud(self, enrich_mock):
        order = self.create_order(phone="03124590872")
        order.customer.multiple_names_detected = True
        order.customer.save(update_fields=["multiple_names_detected"])
        enrich_mock.return_value = build_enrichment()

        result = RiskScoringEngine.calculate(order)
        factor_names = {factor["name"] for factor in result.factors}

        self.assertIn("Multiple Names On Same Number", factor_names)

    def test_area_rto_rate_uses_real_history_above_min_sample(self):
        from apps.risk_engine.enrichment import (
            AREA_RTO_MIN_SAMPLE,
            calculate_area_rto_rate,
        )

        statuses = (["rto"] * 3) + (["delivered"] * 3)
        self.assertGreaterEqual(len(statuses), AREA_RTO_MIN_SAMPLE)
        for index, order_status in enumerate(statuses):
            order = self.create_order(
                phone=f"0312000{index:04d}",
                city="Quetta",
                full_address=f"House {index}, Street 1, Satellite Town, Quetta",
            )
            order.status = order_status
            order.save(update_fields=["status"])

        rate = calculate_area_rto_rate(
            Order.objects.filter(merchant=self.user), "quetta"
        )
        self.assertEqual(rate, 50.0)

    def test_area_rto_rate_returns_none_below_min_sample(self):
        from apps.risk_engine.enrichment import calculate_area_rto_rate

        order = self.create_order(city="Gwadar", full_address="House 1, Street 1, Gwadar")
        order.status = "rto"
        order.save(update_fields=["status"])

        rate = calculate_area_rto_rate(
            Order.objects.filter(merchant=self.user), "gwadar"
        )
        self.assertIsNone(rate)

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_score_and_save_writes_feature_snapshot(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        from apps.orders.models import OrderFeatureSnapshot
        from apps.risk_engine.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION

        order = self.create_order()
        enrich_mock.return_value = build_enrichment()
        RiskScoringEngine.score_and_save(order)

        snaps = OrderFeatureSnapshot.objects.filter(order=order)
        self.assertEqual(snaps.count(), 1)
        snap = snaps.first()
        self.assertEqual(snap.feature_schema_version, FEATURE_SCHEMA_VERSION)
        self.assertEqual(snap.snapshot_type, "online_scoring")
        self.assertTrue(snap.feature_hash)
        # The persisted vector matches the declared contract exactly (no drift).
        self.assertEqual(set(snap.features.keys()), set(FEATURE_NAMES))

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_identical_rescore_does_not_duplicate_snapshot(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        from apps.orders.models import OrderFeatureSnapshot

        order = self.create_order()
        enrich_mock.return_value = build_enrichment()
        RiskScoringEngine.score_and_save(order)
        RiskScoringEngine.score_and_save(order)  # identical inputs → no new row

        self.assertEqual(OrderFeatureSnapshot.objects.filter(order=order).count(), 1)

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_changed_inputs_append_new_snapshot(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        from apps.orders.models import OrderFeatureSnapshot

        order = self.create_order()
        enrich_mock.return_value = build_enrichment()
        RiskScoringEngine.score_and_save(order)

        order.customer.is_blacklisted = True
        order.customer.save(update_fields=["is_blacklisted"])
        enrich_mock.return_value = build_enrichment()
        RiskScoringEngine.score_and_save(order)

        snaps = OrderFeatureSnapshot.objects.filter(order=order)
        self.assertEqual(snaps.count(), 2)
        # Hashes differ because is_blacklisted flipped.
        self.assertEqual(len({s.feature_hash for s in snaps}), 2)

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_merchant_policy_overrides_decision_thresholds(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        from apps.risk_engine.models import MerchantRiskPolicy

        # An order whose enrichment pushes RTO into the 50s: default policy
        # (rto_high=70) keeps it medium; a strict policy (rto_high=40) makes it high.
        def fresh_order(phone):
            return self.create_order(
                phone=phone,
                full_address="House 1, Street 1, Saddar, Quetta",
                city="Quetta",
                total_orders=1,
                delivered_count=0,
                rto_count=0,
            )

        enrich_mock.return_value = build_enrichment(area_rto_rate=80.0, contactability_score=20.0)
        default_order = fresh_order("03120000001")
        default_result = RiskScoringEngine.calculate(default_order)

        MerchantRiskPolicy.objects.create(
            merchant=self.user, rto_high_threshold=40.0, rto_medium_threshold=20.0
        )
        enrich_mock.return_value = build_enrichment(area_rto_rate=80.0, contactability_score=20.0)
        strict_order = fresh_order("03120000002")
        strict_result = RiskScoringEngine.calculate(strict_order)

        self.assertGreaterEqual(strict_result.rto_probability_score, 40.0)
        self.assertEqual(default_result.risk_level, "medium")
        self.assertEqual(strict_result.risk_level, "high")
        self.assertEqual(strict_result.decision_policy_version, "policy-v1")

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_decision_record_written_once_then_deduped(self, enrich_mock, auto_trigger_mock):
        del auto_trigger_mock
        from apps.risk_engine.models import RiskDecisionRecord

        order = self.create_order()
        enrich_mock.return_value = build_enrichment()
        RiskScoringEngine.score_and_save(order)
        RiskScoringEngine.score_and_save(order)  # identical decision → no new record

        records = RiskDecisionRecord.objects.filter(order=order)
        self.assertEqual(records.count(), 1)
        rec = records.first()
        self.assertEqual(rec.recommended_action, order.recommended_action)
        self.assertTrue(rec.feature_hash)
        self.assertEqual(rec.decision_policy_version, "policy-v1")

    def test_score_calibration_service_stays_serializer_compatible(self):
        calibrated = ScoreCalibrationService.calibrate(
            target="fraud",
            score=62,
            version="compat-v1",
        )

        self.assertEqual(calibrated.version, "compat-v1")
        self.assertEqual(calibrated.target, "fraud")
        self.assertEqual(calibrated.probability, 62.0)
        self.assertLess(calibrated.confidence_low, calibrated.probability)
        self.assertGreater(calibrated.confidence_high, calibrated.probability)
        self.assertTrue(calibrated.is_estimated)


class MetricsAndCalibrationTests(TestCase):
    def test_roc_auc_matches_known_value(self):
        from apps.risk_engine.metrics import roc_auc

        # Classic worked example → AUC 0.75.
        self.assertEqual(roc_auc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]), 0.75)
        # Undefined with a single class present.
        self.assertIsNone(roc_auc([1, 1, 1], [0.2, 0.5, 0.9]))

    def test_isotonic_fit_is_monotonic_and_covers_domain(self):
        from apps.risk_engine.metrics import fit_isotonic

        bins = fit_isotonic([10, 20, 30, 40, 50], [0, 0, 1, 0, 1])
        probs = [b.probability for b in bins]
        self.assertEqual(probs, sorted(probs))  # non-decreasing
        self.assertEqual(bins[0].score_lo, 0.0)
        self.assertEqual(bins[-1].score_hi, 100.0)

    def test_precision_recall_table_counts(self):
        from apps.risk_engine.metrics import precision_recall_table

        labels = [1, 1, 0, 0]
        scores = [80, 40, 60, 10]
        row = precision_recall_table(labels, scores, [50])[0]
        # score>=50 flags the 80 (TP) and 60 (FP).
        self.assertEqual(row.true_positive, 1)
        self.assertEqual(row.false_positive, 1)
        self.assertEqual(row.precision, 0.5)
        self.assertEqual(row.recall, 0.5)

    def test_fit_and_serve_returns_outcome_backed_probability(self):
        from apps.risk_engine.calibration import fit_and_activate, serve

        # Low scores never RTO, high scores always do.
        scores = [10, 15, 20, 80, 85, 90]
        labels = [0, 0, 0, 1, 1, 1]
        fit_and_activate(
            target="rto", scores=scores, labels=labels, version="rto-test-v1"
        )

        high = serve("rto", 85, default_version="x")
        low = serve("rto", 15, default_version="x")

        self.assertEqual(high.source, "isotonic")
        self.assertFalse(high.is_estimated)
        self.assertGreater(high.probability, low.probability)
        self.assertEqual(high.probability, 100.0)
        self.assertEqual(low.probability, 0.0)

    def test_serve_without_model_is_flagged_uncalibrated(self):
        from apps.risk_engine.calibration import serve

        served = serve("fraud", 70, default_version="rule-based-v1")
        self.assertEqual(served.source, "uncalibrated")
        self.assertTrue(served.is_estimated)
        self.assertEqual(served.probability, 70.0)
        self.assertEqual(served.sample_size, 0)


class MLModelUnitTests(TestCase):
    def test_logistic_regression_learns_separable_signal(self):
        import random

        from apps.risk_engine.metrics import roc_auc
        from apps.risk_engine.ml import fit_logistic

        rng = random.Random(0)
        feats, labels = [], []
        for _ in range(300):
            # area_rto_rate carries the signal; everything else is noise.
            high = rng.random() < 0.5
            feats.append({
                "area_rto_rate": rng.uniform(60, 100) if high else rng.uniform(0, 30),
                "amount": rng.uniform(0, 10000),
            })
            labels.append(1 if high else 0)
        model = fit_logistic(feats, labels, feature_order=["area_rto_rate", "amount"], epochs=300)

        probs = [model.predict_proba(f) for f in feats]
        self.assertGreater(roc_auc(labels, probs), 0.9)
        # Serialization round-trips.
        from apps.risk_engine.ml import LogisticModel
        restored = LogisticModel.from_dict(model.to_dict())
        self.assertAlmostEqual(
            restored.predict_proba(feats[0]), model.predict_proba(feats[0]), places=9
        )


def _constant_ml_params(bias: float):
    """A LogisticModel dict whose zero weights make it output sigmoid(bias)."""
    from apps.risk_engine.ml import ML_FEATURE_ORDER

    d = len(ML_FEATURE_ORDER)
    return {
        "feature_order": ML_FEATURE_ORDER,
        "means": [0.0] * d,
        "stds": [1.0] * d,
        "weights": [0.0] * d,
        "bias": bias,
    }


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class MLServingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ml@example.com", username="ml", first_name="M", last_name="L",
            password="StrongPass123!",
        )

    def _order(self, phone="03124590876"):
        customer = Customer.objects.create(
            merchant=self.user, name="Ali Raza", phone=phone, city="Islamabad",
            total_orders=3, delivered_count=2, rto_count=0,
        )
        address = Address.objects.create(
            customer=customer, full_address="House 22, Street 5, G-11, Islamabad",
            city="Islamabad", district="G-11", province="Punjab", postal_code="44000",
            confidence_score=80, status="valid",
        )
        return Order.objects.create(
            order_id=f"ML-{phone[-4:]}", merchant=self.user, customer=customer,
            address=address, amount=Decimal("2500.00"), payment_method="cod",
            status="pending", chat_status="unverified",
        )

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_shadow_model_records_but_does_not_change_decision(self, enrich_mock, _auto):
        from apps.risk_engine.models import RiskDecisionRecord, RiskMLModel

        enrich_mock.return_value = build_enrichment()
        baseline = RiskScoringEngine.calculate(self._order("03124590801"))

        # Active SHADOW model that screams "RTO" (sigmoid(10) ≈ 1.0).
        RiskMLModel.objects.create(
            target="rto", version="shadow-v1", role="shadow", is_active=True,
            params=_constant_ml_params(10.0),
        )
        enrich_mock.return_value = build_enrichment()
        order = self._order("03124590802")
        result = RiskScoringEngine.score_and_save(order)

        # Decision is unchanged (rules still champion)…
        self.assertEqual(result.risk_level, baseline.risk_level)
        self.assertEqual(result.recommended_action, baseline.recommended_action)
        self.assertEqual(result.score_source, "rules")
        # …but the shadow prediction is recorded for later comparison.
        self.assertIsNotNone(result.ml_rto_probability)
        self.assertGreater(result.ml_rto_probability, 90.0)
        rec = RiskDecisionRecord.objects.filter(order=order).latest("created_at")
        self.assertEqual(rec.ml_model_version, "shadow-v1")
        self.assertGreater(rec.ml_rto_probability, 90.0)

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_champion_model_drives_rto_and_elevates_risk(self, enrich_mock, _auto):
        from apps.risk_engine.models import RiskMLModel

        RiskMLModel.objects.create(
            target="rto", version="champ-v1", role="champion", is_active=True,
            params=_constant_ml_params(10.0),  # ≈ 100% RTO
        )
        enrich_mock.return_value = build_enrichment()
        result = RiskScoringEngine.calculate(self._order("03124590803"))

        self.assertGreater(result.rto_probability_score, 90.0)
        self.assertEqual(result.risk_level, "high")
        self.assertEqual(result.score_source, "hybrid")

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_champion_does_not_suppress_hard_blacklist_guardrail(self, enrich_mock, _auto):
        from apps.risk_engine.models import RiskMLModel

        # Champion that says "very safe" (sigmoid(-10) ≈ 0) must NOT rescue a
        # blacklisted customer — the hard guardrail still forces cancel.
        RiskMLModel.objects.create(
            target="rto", version="champ-safe", role="champion", is_active=True,
            params=_constant_ml_params(-10.0),
        )
        order = self._order("03124590804")
        order.customer.is_blacklisted = True
        order.customer.save(update_fields=["is_blacklisted"])
        enrich_mock.return_value = build_enrichment()
        result = RiskScoringEngine.calculate(order)

        self.assertEqual(result.recommended_action, "cancel_order")
        self.assertEqual(result.risk_level, "high")


@override_settings(ADDRESS_VALIDATION_PROVIDER="internal_heuristic")
class ScoreOrderApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant-api@example.com",
            username="merchant_api",
            first_name="Merchant",
            last_name="Api",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)

        customer = Customer.objects.create(
            merchant=self.user,
            name="Ahmed Khan",
            phone="03124590876",
            city="Lahore",
            total_orders=2,
            delivered_count=1,
            rto_count=0,
        )
        address = Address.objects.create(
            customer=customer,
            full_address="House 10, Street 2, Model Town, Lahore",
            city="Lahore",
            district="Model Town",
            province="Punjab",
            postal_code="54000",
            confidence_score=82,
            status="valid",
        )
        self.order = Order.objects.create(
            order_id="ORD-API-1",
            merchant=self.user,
            customer=customer,
            address=address,
            amount=Decimal("1800.00"),
            payment_method="cod",
            status="pending",
        )

    @patch("apps.chatbot.services.ConversationService.auto_trigger_if_needed")
    @patch("apps.stores.shopify_sync.refresh_shopify_order_bootstrap")
    @patch("apps.risk_engine.services.OrderEnrichmentService.enrich")
    def test_score_endpoint_returns_rule_engine_payload(self, enrich_mock, refresh_mock, auto_trigger_mock):
        del refresh_mock
        del auto_trigger_mock
        enrich_mock.return_value = build_enrichment()

        response = self.client.post(
            "/api/risk/score/",
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["order_id"], self.order.order_id)
        self.assertEqual(response.data["risk_level"], "low")
        self.assertEqual(response.data["recommended_action"], "ship_order")
        self.assertIn("information_quality", response.data)
        self.assertIn("decision_summary", response.data)
