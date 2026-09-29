import base64
import io
import json
import urllib.error
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.payaza import (
    fetch_main_account_enquiry,
    fetch_main_accounts,
    fetch_main_accounts_requests,
    payaza_authorization_value,
)

DOCUMENTED_MAIN_ACCOUNTS_URL = "https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts"
ACCOUNT_ENQUIRY_URL = "https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts/merchant/enquiry/main"


def _json_response(status, payload):
    body = json.dumps(payload).encode("utf-8")

    class FakeResponse:
        def __init__(self):
            self.status = status

        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    return FakeResponse()


@override_settings(
    DEBUG=True,
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY="secret-test-key",
    PAYAZA_TENANT_ID="test",
)
class PayazaConnectionTests(TestCase):
    def test_main_accounts_request_uses_documented_url_and_headers(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            return _json_response(200, {"message": "ok", "data": []})

        with patch("users.payaza.urllib.request.urlopen", side_effect=fake_urlopen):
            result = fetch_main_accounts()

        request = captured["request"]
        authorization = request.get_header("Authorization")
        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")
        header_text = " ".join(f"{name}:{value}" for name, value in request.header_items())

        self.assertTrue(result["success"])
        self.assertEqual(request.full_url, DOCUMENTED_MAIN_ACCOUNTS_URL)
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("X-tenantid"), "test")
        self.assertIsNotNone(authorization)
        self.assertTrue(authorization.startswith("Payaza "))
        self.assertFalse(authorization.startswith("Bearer"))
        self.assertEqual(authorization, f"Payaza {encoded_public_key}")
        self.assertNotIn("public-test-key", authorization)
        self.assertNotIn("secret-test-key", header_text)
        self.assertNotIn("public-test-key", header_text)

    def test_authorization_uses_payaza_prefix_and_base64_public_key(self):
        encoded = base64.b64encode(b"public-test-key").decode("ascii")
        self.assertEqual(payaza_authorization_value("public-test-key"), f"Payaza {encoded}")
        self.assertNotIn("Bearer", payaza_authorization_value("public-test-key"))
        self.assertNotIn("secret-test-key", payaza_authorization_value("public-test-key"))

    def test_successful_account_response_is_sanitized(self):
        payload = {
            "status": "success",
            "message": "Accounts retrieved",
            "data": [
                {"account_name": "Main KES", "currency": "KES", "country": "KE", "status": "active"},
            ],
            "secret_key": "should-not-leak",
        }
        with patch("users.payaza.urllib.request.urlopen", return_value=_json_response(200, payload)):
            response = self.client.get(reverse("payaza-test-connection"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["http_status"], 200)
        self.assertEqual(body["accounts"][0]["currency"], "KES")
        self.assertNotIn("public-test-key", response.content.decode())
        self.assertNotIn("secret-test-key", response.content.decode())
        self.assertNotIn("should-not-leak", response.content.decode())

    def test_authentication_failure_is_sanitized(self):
        error = urllib.error.HTTPError(
            url="https://api.payaza.africa/live/payaza-account/api/v1/mainaccounts",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Invalid API key public-test-key"}'),
        )
        with patch("users.payaza.urllib.request.urlopen", side_effect=error):
            response = self.client.get(reverse("payaza-test-connection"))

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"], "authentication_failed")
        self.assertEqual(body["http_status"], 401)
        self.assertNotIn("public-test-key", response.content.decode())

    @override_settings(PAYAZA_PUBLIC_KEY="", PAYAZA_SECRET_KEY="secret-test-key")
    def test_missing_public_key(self):
        response = self.client.get(reverse("payaza-test-connection"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "missing_configuration")
        self.assertIn("PAYAZA_PUBLIC_KEY", response.json()["message"])

    @override_settings(PAYAZA_PUBLIC_KEY="public-test-key", PAYAZA_SECRET_KEY="")
    def test_missing_secret_key(self):
        response = self.client.get(reverse("payaza-test-connection"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "missing_configuration")
        self.assertIn("PAYAZA_SECRET_KEY", response.json()["message"])

    @override_settings(DEBUG=False)
    def test_endpoint_is_hidden_when_debug_is_off(self):
        response = self.client.get(reverse("payaza-test-connection"))
        self.assertEqual(response.status_code, 404)


class _RequestsResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.text = json.dumps(payload)


@override_settings(
    DEBUG=True,
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY="secret-test-key",
    PAYAZA_TENANT_ID="test",
)
class PayazaRequestsDiagnosticTests(TestCase):
    def test_requests_call_matches_documented_example(self):
        captured = {}

        def fake_get(url, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return _RequestsResponse(200, {"message": "ok", "data": []})

        with patch("users.payaza.requests.get", side_effect=fake_get):
            result = fetch_main_accounts_requests()

        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")
        authorization = captured["headers"]["Authorization"]
        self.assertEqual(captured["url"], DOCUMENTED_MAIN_ACCOUNTS_URL)
        self.assertEqual(set(captured["headers"]), {"Authorization", "X-TenantID"})
        self.assertEqual(captured["headers"]["X-TenantID"], "test")
        self.assertTrue(authorization.startswith("Payaza "))
        self.assertFalse(authorization.startswith("Bearer"))
        self.assertEqual(authorization, f"Payaza {encoded_public_key}")
        self.assertNotIn("public-test-key", authorization)
        self.assertNotIn("secret-test-key", authorization)
        self.assertEqual(result["client"], "requests")
        self.assertTrue(result["success"])
        self.assertNotIn("public-test-key", json.dumps(result))
        self.assertNotIn("secret-test-key", json.dumps(result))
        self.assertNotIn(encoded_public_key, json.dumps(result))

    def test_requests_diagnostic_does_not_log_credentials(self):
        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")

        with patch(
            "users.payaza.requests.get",
            return_value=_RequestsResponse(200, {"message": "ok", "data": []}),
        ):
            with self.assertLogs("users.payaza", level="INFO") as logs:
                fetch_main_accounts_requests()

        logged = "\n".join(logs.output)
        self.assertIn(DOCUMENTED_MAIN_ACCOUNTS_URL, logged)
        self.assertNotIn("public-test-key", logged)
        self.assertNotIn("secret-test-key", logged)
        self.assertNotIn(encoded_public_key, logged)
        self.assertNotIn("Authorization", logged)

    def test_requests_http_error_is_sanitized(self):
        payload = {"message": "Invalid API key public-test-key", "status": 401}
        with patch("users.payaza.requests.get", return_value=_RequestsResponse(401, payload)):
            response = self.client.get(reverse("payaza-test-connection-requests"))

        self.assertEqual(response.status_code, 502)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["client"], "requests")
        self.assertEqual(body["error"], "authentication_failed")
        self.assertEqual(body["http_status"], 401)
        self.assertNotIn("public-test-key", response.content.decode())
        self.assertNotIn("secret-test-key", response.content.decode())
        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")
        self.assertNotIn(encoded_public_key, response.content.decode())

    @override_settings(DEBUG=False)
    def test_requests_endpoint_is_hidden_when_debug_is_off(self):
        response = self.client.get(reverse("payaza-test-connection-requests"))
        self.assertEqual(response.status_code, 404)


@override_settings(
    DEBUG=True,
    PAYAZA_PUBLIC_KEY="public-test-key",
    PAYAZA_SECRET_KEY="secret-test-key",
    PAYAZA_TENANT_ID="test",
)
class PayazaAccountEnquiryTests(TestCase):
    def test_enquiry_uses_confirmed_url_and_auth_without_the_secret(self):
        captured = {}

        def fake_get(url, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = dict(headers or {})
            captured["timeout"] = timeout
            return _RequestsResponse(200, {
                "message": "Account enquiry response public-test-key",
                "status": True,
                "secret_key": "secret-test-key",
                "data": [
                    {
                        "accountName": "Test Merchant",
                        "currency": "NGN",
                        "country": "NGA",
                        "status": "ACTIVE",
                        "virtualAccounts": [{"accountNumber": "99926838326"}],
                    },
                ],
            })

        with patch("users.payaza.requests.get", side_effect=fake_get):
            with self.assertLogs("users.payaza", level="INFO") as logs:
                result = fetch_main_account_enquiry()

        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")
        authorization = captured["headers"]["Authorization"]
        header_text = json.dumps(captured["headers"])
        logged = "\n".join(logs.output)
        rendered = json.dumps(result)

        self.assertEqual(captured["url"], ACCOUNT_ENQUIRY_URL)
        self.assertEqual(set(captured["headers"]), {"Authorization", "X-TenantID"})
        self.assertEqual(captured["headers"]["X-TenantID"], "test")
        self.assertTrue(authorization.startswith("Payaza "))
        self.assertEqual(authorization, f"Payaza {encoded_public_key}")
        self.assertNotIn("public-test-key", authorization)
        self.assertNotIn("secret-test-key", header_text)
        self.assertNotIn("secret-test-key", rendered)
        self.assertNotIn("public-test-key", rendered)
        self.assertNotIn(encoded_public_key, rendered)
        self.assertNotIn("99926838326", rendered)
        self.assertNotIn("Authorization", logged)
        self.assertNotIn("public-test-key", logged)
        self.assertNotIn("secret-test-key", logged)
        self.assertNotIn(encoded_public_key, logged)
        self.assertTrue(result["success"])
        self.assertEqual(result["accounts"][0]["name"], "Test Merchant")
        self.assertEqual(result["accounts"][0]["currency"], "NGN")
        self.assertEqual(result["accounts"][0]["country"], "NGA")
        self.assertEqual(result["client"], "account-enquiry")

    def test_enquiry_http_error_is_sanitized(self):
        payload = {"message": "Invalid API key public-test-key", "status": 401}
        with patch("users.payaza.requests.get", return_value=_RequestsResponse(401, payload)):
            response = self.client.get(reverse("payaza-test-account-enquiry"))

        self.assertEqual(response.status_code, 502)
        body = response.json()
        encoded_public_key = base64.b64encode(b"public-test-key").decode("ascii")
        self.assertFalse(body["success"])
        self.assertEqual(body["error"], "authentication_failed")
        self.assertEqual(body["http_status"], 401)
        self.assertEqual(body["accounts"], [])
        rendered = response.content.decode()
        self.assertNotIn("public-test-key", rendered)
        self.assertNotIn("secret-test-key", rendered)
        self.assertNotIn(encoded_public_key, rendered)

    @override_settings(PAYAZA_PUBLIC_KEY="")
    def test_enquiry_missing_configuration(self):
        response = self.client.get(reverse("payaza-test-account-enquiry"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "missing_configuration")

    @override_settings(DEBUG=False)
    def test_enquiry_endpoint_is_hidden_when_debug_is_off(self):
        response = self.client.get(reverse("payaza-test-account-enquiry"))
        self.assertEqual(response.status_code, 404)
