import base64
import hashlib
import hmac
import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import requests
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import Earnings, Job, Payment, Payout, User

SECRET = "secret-test-key"
PIN = "419374"
ACCOUNT_REFERENCE = "1010000009"
VERIFIED_KES_ACCOUNT_REFERENCE = "5010154966"
BANK_CODE = "SAFKEN"
TRANSFER_URL = "https://api.payaza.africa/live/payout-receptor/payout"
STATUS_URL = "https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts/transaction/status"


def _sign(raw_body):
    digest = hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha512).digest()
    return base64.b64encode(digest).decode("ascii")


def _user(username, role, first_name="Amina", last_name="Otieno", phone="+254712345678"):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="test-pass-123",
        role=role,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone,
    )


class _Response:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)


def _initiated_body(session_id=None):
    content = {
        "transaction_status": "09",
        "response_status": "TRANSACTION_INITIATED",
        "response_description": "Transaction has been successfully submitted for processing",
    }
    if session_id:
        content["session_id"] = session_id
    return {
        "response_code": 200,
        "response_message": "Request successfully submitted",
        "response_content": content,
        "resp_code": "09",
    }


def _status_body(transaction_status, response_code="00"):
    return {
        "message": "Transaction fetched",
        "status": True,
        "data": {
            "transactionStatus": transaction_status,
            "responseCode": response_code,
        },
    }


@override_settings(
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY=SECRET,
    PAYAZA_TENANT_ID="test",
    PAYAZA_TRANSACTION_PIN=PIN,
    PAYAZA_KES_ACCOUNT_REFERENCE=ACCOUNT_REFERENCE,
    PAYAZA_PAYOUT_BANK_CODE=BANK_CODE,
    PAYAZA_SENDER_NAME="KaziBridge",
    PAYAZA_SENDER_PHONE="254700000001",
    PAYAZA_SENDER_ADDRESS="Nairobi",
)
class PayazaPayoutTests(TestCase):
    def setUp(self):
        self.client_user = _user("client", "CLIENT")
        self.freelancer = _user("freelancer", "FREELANCER")
        self.other = _user("other", "CLIENT")
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)
        self.other_api = APIClient()
        self.other_api.force_authenticate(self.other)
        self.payment = self._received_payment()
        self.payout = self._payout()

    def _received_payment(self, amount=Decimal("2500.00")):
        job = Job.objects.create(
            title="Graphic Design",
            description="Work",
            budget=amount,
            deadline=date(2026, 10, 30),
            created_by=self.client_user,
            status="COMPLETED",
        )
        payment = Payment.objects.create(
            job=job,
            client=self.client_user,
            freelancer=self.freelancer,
            amount=amount,
            currency="KES",
        )
        payment.transition_to(Payment.PAYMENT_PROCESSING)
        payment.transition_to(Payment.PAYMENT_RECEIVED)
        return payment

    def _payout(self, payment=None):
        payment = payment or self.payment
        return Payout.objects.create(
            payment=payment,
            freelancer=payment.freelancer,
            amount=Decimal("1.00"),
            currency="USD",
            destination_country="KE",
            destination_currency="KES",
            payout_method="MOBILE_MONEY",
        )

    def _post(self, api=None, payout=None):
        payout = payout or self.payout
        return (api or self.api).post(reverse("payout-payaza", args=[payout.id]), {}, format="json")

    def test_payout_creation_requires_received_payment_and_uses_payment_facts(self):
        pending = Payment.objects.create(
            job=Job.objects.create(
                title="Open work",
                description="Work",
                budget=Decimal("900.00"),
                deadline=date(2026, 10, 30),
                created_by=self.client_user,
                status="IN_PROGRESS",
            ),
            client=self.client_user,
            freelancer=self.freelancer,
            amount=Decimal("900.00"),
            currency="KES",
        )
        rejected = self.api.post(
            reverse("payouts"),
            {
                "payment": pending.id,
                "amount": "1.00",
                "destination_country": "KE",
                "destination_currency": "KES",
                "payout_method": "MOBILE_MONEY",
            },
            format="json",
        )
        fresh = self._received_payment()
        created = self.api.post(
            reverse("payouts"),
            {
                "payment": fresh.id,
                "amount": "1.00",
                "freelancer": self.other.id,
                "destination_country": "KE",
                "destination_currency": "KES",
                "payout_method": "MOBILE_MONEY",
            },
            format="json",
        )
        payout = Payout.objects.get(pk=created.data["id"])
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(payout.amount, Decimal("2500.00"))
        self.assertEqual(payout.freelancer_id, self.freelancer.id)
        self.assertEqual(payout.currency, "KES")

    def test_valid_kes_payload_maps_country_and_does_not_mark_paid(self):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _Response(200, _initiated_body())

        with patch("users.payaza.requests.post", side_effect=fake_post) as post:
            response = self._post()

        self.payout.refresh_from_db()
        beneficiary = captured["json"]["service_payload"]["payout_beneficiaries"][0]
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(captured["url"], TRANSFER_URL)
        self.assertNotIn("X-ProductID", captured["headers"])
        self.assertEqual(captured["headers"]["X-TenantID"], "test")
        self.assertTrue(captured["headers"]["Authorization"].startswith("Payaza "))
        self.assertEqual(captured["json"]["transaction_type"], "mobile_money")
        sent = json.dumps(captured["json"])
        self.assertEqual(captured["json"]["service_payload"]["country"], "KEN")
        self.assertEqual(captured["json"]["service_payload"]["currency"], "KES")
        self.assertEqual(captured["json"]["service_payload"]["account_reference"], ACCOUNT_REFERENCE)
        self.assertEqual(captured["json"]["service_payload"]["payout_amount"], 2500.0)
        self.assertEqual(captured["json"]["service_payload"]["transaction_pin"], int(PIN))
        self.assertEqual(beneficiary["credit_amount"], 2500.0)
        self.assertEqual(beneficiary["account_number"], "254712345678")
        self.assertNotIn(VERIFIED_KES_ACCOUNT_REFERENCE, sent)
        self.assertNotIn("TZS", sent)
        self.assertNotIn("TZA", sent)
        self.assertEqual(beneficiary["account_name"], "Amina Otieno")
        self.assertEqual(beneficiary["bank_code"], "SAFKEN")
        self.assertEqual(beneficiary["narration"], "KaziBridge payout")
        self.assertEqual(beneficiary["transaction_reference"], self.payout.transaction_reference)
        self.assertTrue(self.payout.transaction_reference.startswith("KZB-PAYOUT-"))
        self.assertEqual(self.payout.destination_country, "KE")
        self.assertEqual(self.payout.destination_currency, "KES")
        self.assertEqual(self.payout.status, Payout.PAYOUT_PROCESSING)
        self.assertFalse(self.payout.provider_transaction_reference)
        self.assertNotIn(PIN, json.dumps(body))
        self.assertNotIn(SECRET, json.dumps(body))

    def test_missing_freelancer_names_and_phone_are_rejected(self):
        self.freelancer.first_name = ""
        self.freelancer.save(update_fields=["first_name"])
        with patch("users.payaza.requests.post") as post:
            missing_first = self._post()
        self.freelancer.first_name = "Amina"
        self.freelancer.last_name = ""
        self.freelancer.save(update_fields=["first_name", "last_name"])
        with patch("users.payaza.requests.post") as post_last:
            missing_last = self._post()
        self.freelancer.last_name = "Otieno"
        self.freelancer.phone_number = "+254000000000"
        self.freelancer.save(update_fields=["last_name", "phone_number"])
        with patch("users.payaza.requests.post") as post_phone:
            bad_phone = self._post()
        self.payout.refresh_from_db()
        self.assertEqual(missing_first.json()["error"], "missing_freelancer_information")
        self.assertIn("customer_first_name", missing_first.json()["message"])
        self.assertEqual(missing_last.json()["error"], "missing_freelancer_information")
        self.assertIn("customer_last_name", missing_last.json()["message"])
        self.assertEqual(bad_phone.json()["error"], "missing_freelancer_information")
        self.assertIn("account_number", bad_phone.json()["message"])
        self.payment.refresh_from_db()
        earning = Earnings.objects.get(payment=self.payment)
        self.assertEqual(self.payout.status, Payout.PAYOUT_PENDING)
        self.assertFalse(self.payout.provider_transaction_reference)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(earning.amount, Decimal("2500.00"))
        self.assertIsNone(earning.payout_id)
        self.assertEqual(Payout.objects.filter(payment=self.payment).count(), 1)
        post.assert_not_called()
        post_last.assert_not_called()
        post_phone.assert_not_called()

    def _assert_config_blocks_payout(self, response, post, error, message):
        self.payout.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], error)
        self.assertEqual(response.json()["message"], message)
        self.payment.refresh_from_db()
        earning = Earnings.objects.get(payment=self.payment)
        self.assertEqual(self.payout.status, Payout.PAYOUT_PENDING)
        self.assertFalse(self.payout.provider_transaction_reference)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(earning.amount, Decimal("2500.00"))
        self.assertIsNone(earning.payout_id)
        self.assertEqual(Payout.objects.filter(payment=self.payment).count(), 1)
        post.assert_not_called()
        body = json.dumps(response.json())
        self.assertNotIn(PIN, body)
        self.assertNotIn(SECRET, body)
        self.assertNotIn("public-test-key", body)
        self.assertNotIn("Authorization", body)

    @override_settings(PAYAZA_PAYOUT_BANK_CODE="")
    def test_missing_payout_bank_code_is_rejected(self):
        with patch("users.payaza.requests.post") as post:
            response = self._post()
        self._assert_config_blocks_payout(
            response,
            post,
            "missing_payout_bank_code",
            "Payaza KES mobile-money payout bank code has not been configured.",
        )
        body = json.dumps(response.json())
        for code in ("SAFKEN", "MPESA", "TIGTZA", "AIRTZA", "HALTZA", "VODTZA", "TZS", "TZA"):
            self.assertNotIn(code, body)

    @override_settings(PAYAZA_TRANSACTION_PIN="")
    def test_missing_transaction_pin_is_rejected(self):
        with patch("users.payaza.requests.post") as post:
            response = self._post()
        self._assert_config_blocks_payout(
            response,
            post,
            "missing_transaction_pin",
            "Payaza transaction PIN is not configured.",
        )

    @override_settings(PAYAZA_KES_ACCOUNT_REFERENCE="")
    def test_missing_kes_account_reference_is_rejected(self):
        with patch("users.payaza.requests.post") as post:
            response = self._post()
        self._assert_config_blocks_payout(
            response,
            post,
            "missing_kes_account_reference",
            "Payaza KES account reference is not configured.",
        )

    def test_missing_sender_configuration_is_rejected(self):
        cases = (
            {"PAYAZA_SENDER_NAME": ""},
            {"PAYAZA_SENDER_PHONE": ""},
            {"PAYAZA_SENDER_ADDRESS": ""},
        )
        for settings_override in cases:
            with self.subTest(settings_override=settings_override):
                with override_settings(**settings_override):
                    with patch("users.payaza.requests.post") as post:
                        response = self._post()
                self._assert_config_blocks_payout(
                    response,
                    post,
                    "missing_payout_configuration",
                    "Payaza sender details are not configured.",
                )

    @override_settings(PAYAZA_KES_ACCOUNT_REFERENCE=VERIFIED_KES_ACCOUNT_REFERENCE)
    def test_configured_kes_account_reference_is_sent_and_not_returned(self):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["json"] = json
            return _Response(200, _initiated_body())

        with patch("users.payaza.requests.post", side_effect=fake_post):
            response = self._post()

        body = json.dumps(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            captured["json"]["service_payload"]["account_reference"],
            VERIFIED_KES_ACCOUNT_REFERENCE,
        )
        self.assertEqual(captured["json"]["service_payload"]["currency"], "KES")
        self.assertEqual(captured["json"]["service_payload"]["country"], "KEN")
        self.assertNotIn("TZS", json.dumps(captured["json"]))
        self.assertNotIn(VERIFIED_KES_ACCOUNT_REFERENCE, body)
        self.assertNotIn(PIN, body)
        self.assertNotIn(SECRET, body)
        self.assertNotIn("public-test-key", body)
        self.assertNotIn("Authorization", body)

    def test_provider_reference_is_stored_only_when_payaza_returns_one(self):
        with patch("users.payaza.requests.post", return_value=_Response(200, _initiated_body("sess-9"))):
            response = self._post()
        self.payout.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.payout.provider_transaction_reference, "sess-9")
        self.assertNotEqual(self.payout.provider_transaction_reference, self.payout.transaction_reference)

    def test_unauthorized_processing_and_paid_payouts_are_not_sent_again(self):
        with patch("users.payaza.requests.post") as post:
            forbidden = self.other_api.post(reverse("payout-payaza", args=[self.payout.id]), {}, format="json")
            anonymous = APIClient().post(reverse("payout-payaza", args=[self.payout.id]), {}, format="json")
        self.assertEqual(forbidden.status_code, 404)
        self.assertEqual(anonymous.status_code, 401)
        self.payout.transition_to(Payout.PAYOUT_PROCESSING)
        with patch("users.payaza.requests.post") as processing_post:
            processing = self._post()
        self.payout.transition_to(Payout.PAYOUT_PAID)
        with patch("users.payaza.requests.post") as paid_post:
            paid = self._post()
        self.assertEqual(processing.status_code, 400)
        self.assertEqual(processing.json()["error"], "invalid_payout_state")
        self.assertEqual(paid.status_code, 400)
        self.assertEqual(paid.json()["error"], "invalid_payout_state")
        post.assert_not_called()
        processing_post.assert_not_called()
        paid_post.assert_not_called()

    def _status(self, transaction_status, response_code="00"):
        with patch(
            "users.payaza.requests.get",
            return_value=_Response(200, _status_body(transaction_status, response_code)),
        ) as get:
            response = self.api.get(reverse("payout-payaza-status", args=[self.payout.id]))
        self.payout.refresh_from_db()
        return response, get

    def test_status_mapping_for_success_failure_pending_and_escrow(self):
        self.payout.transition_to(Payout.PAYOUT_PROCESSING)
        pending, pending_get = self._status("NIP_PENDING", "09")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(self.payout.status, Payout.PAYOUT_PROCESSING)
        self.assertEqual(pending_get.call_count, 1)
        self.assertEqual(pending_get.call_args.kwargs["params"]["transaction_reference"], self.payout.transaction_reference)
        self.assertIn(STATUS_URL, pending_get.call_args.args[0])
        escrow, _escrow_get = self._status("ESCROW_SUCCESS", "00")
        self.assertEqual(self.payout.status, Payout.PAYOUT_PROCESSING)
        initiated, _initiated_get = self._status("TRANSACTION_INITIATED", "09")
        self.assertEqual(initiated.status_code, 200)
        self.assertEqual(self.payout.status, Payout.PAYOUT_PROCESSING)
        failed, _failed_get = self._status("NIP_FAILURE", "07")
        self.assertEqual(self.payout.status, Payout.PAYOUT_FAILED)
        self.assertTrue(failed.json()["local_status_changed"])
        paid_payout = self._payout(self._received_payment(Decimal("2600.00")))
        paid_payout.transition_to(Payout.PAYOUT_PROCESSING)
        with patch("users.payaza.requests.get", return_value=_Response(200, _status_body("NIP_SUCCESS", "00"))):
            paid = self.api.get(reverse("payout-payaza-status", args=[paid_payout.id]))
        paid_payout.refresh_from_db()
        self.assertEqual(paid.status_code, 200)
        self.assertTrue(paid.json()["local_status_changed"])
        self.assertEqual(paid_payout.status, Payout.PAYOUT_PAID)
        self.assertEqual(Earnings.objects.filter(payment=paid_payout.payment).count(), 1)

    def test_timeout_connection_balance_and_duplicate_do_not_retry(self):
        cases = [
            (requests.Timeout(), 504, "payaza_unavailable"),
            (requests.RequestException(), 502, "payaza_unavailable"),
        ]
        for error, http_status, error_code in cases:
            payout = self._payout(self._received_payment())
            with patch("users.payaza.requests.post", side_effect=error) as post:
                response = self._post(payout=payout)
            payout.refresh_from_db()
            self.assertEqual(response.status_code, http_status)
            self.assertEqual(response.json()["error"], error_code)
            self.assertEqual(payout.status, Payout.PAYOUT_PENDING)
            self.assertEqual(post.call_count, 1)
            self.assertNotIn(PIN, json.dumps(response.json()))
            self.assertNotIn(SECRET, json.dumps(response.json()))

        balance = self._payout(self._received_payment())
        with patch(
            "users.payaza.requests.post",
            return_value=_Response(200, {"response_code": 500, "response_message": "Insufficient Balance"}),
        ) as post:
            response = self._post(payout=balance)
        balance.refresh_from_db()
        self.assertEqual(response.json()["error"], "insufficient_balance")
        self.assertEqual(balance.status, Payout.PAYOUT_PENDING)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(Payout.objects.filter(payment=balance.payment).count(), 1)

        duplicate = self._payout(self._received_payment())
        before = Payout.objects.count()
        with patch(
            "users.payaza.requests.post",
            return_value=_Response(200, {
                "response_code": 0,
                "response_message": "Transaction reference already exists. please use unique reference",
                "resp_code": "X03",
            }),
        ) as post:
            response = self._post(payout=duplicate)
        duplicate.refresh_from_db()
        self.assertEqual(response.json()["error"], "duplicate_reference")
        self.assertEqual(duplicate.status, Payout.PAYOUT_PENDING)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(Payout.objects.count(), before)

    def test_successful_payout_webhook_is_idempotent_and_unknown_reference_creates_nothing(self):
        self.payout.transition_to(Payout.PAYOUT_PROCESSING)
        raw = json.dumps({
            "transaction_reference": self.payout.transaction_reference,
            "transaction_status": "NIP_SUCCESS",
            "response_code": "00",
            "session_id": "sess-webhook",
        }).encode("utf-8")
        with patch("users.payaza.requests.get", return_value=_Response(200, _status_body("NIP_SUCCESS", "00"))) as get:
            first = self.api.post(
                reverse("payout-payaza-webhook"),
                data=raw,
                content_type="application/json",
                HTTP_X_PAYAZA_SIGNATURE=_sign(raw),
            )
            second = self.api.post(
                reverse("payout-payaza-webhook"),
                data=raw,
                content_type="application/json",
                HTTP_X_PAYAZA_SIGNATURE=_sign(raw),
            )
        self.payout.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["local_status_changed"])
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["local_status_changed"])
        self.assertEqual(self.payout.status, Payout.PAYOUT_PAID)
        self.assertEqual(self.payout.provider_transaction_reference, "sess-webhook")
        self.assertEqual(Payout.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(get.call_count, 2)
        unknown = json.dumps({"transaction_reference": "KZB-PAYOUT-DOESNOTEXIST"}).encode("utf-8")
        before = Payout.objects.count()
        with patch("users.payaza.requests.get") as status_check:
            response = self.api.post(
                reverse("payout-payaza-webhook"),
                data=unknown,
                content_type="application/json",
                HTTP_X_PAYAZA_SIGNATURE=_sign(unknown),
            )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"], "unknown_transaction_reference")
        self.assertEqual(Payout.objects.count(), before)
        status_check.assert_not_called()
        self.assertNotIn(PIN, json.dumps(first.json()))
        self.assertNotIn(SECRET, json.dumps(first.json()))

    def test_invalid_payout_webhook_signature_is_rejected(self):
        raw = json.dumps({
            "transaction_reference": self.payout.transaction_reference,
            "transaction_status": "NIP_SUCCESS",
        }).encode("utf-8")
        with patch("users.payaza.requests.get") as status_check:
            response = self.api.post(
                reverse("payout-payaza-webhook"),
                data=raw,
                content_type="application/json",
                HTTP_X_PAYAZA_SIGNATURE="not-a-valid-signature",
            )
        self.payout.refresh_from_db()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "invalid_signature")
        self.assertEqual(self.payout.status, Payout.PAYOUT_PENDING)
        status_check.assert_not_called()

    def test_failed_payout_webhook_marks_failed_without_a_second_earnings_row(self):
        self.payout.transition_to(Payout.PAYOUT_PROCESSING)
        raw = json.dumps({
            "transaction_reference": self.payout.transaction_reference,
            "transaction_status": "NIP_FAILURE",
            "response_code": "07",
        }).encode("utf-8")
        with patch("users.payaza.requests.get", return_value=_Response(200, _status_body("NIP_FAILURE", "07"))):
            response = self.api.post(
                reverse("payout-payaza-webhook"),
                data=raw,
                content_type="application/json",
                HTTP_X_PAYAZA_SIGNATURE=_sign(raw),
            )
        self.payout.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["local_status_changed"])
        self.assertEqual(self.payout.status, Payout.PAYOUT_FAILED)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
