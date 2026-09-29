"""Minimal Payaza Test Mode client.

This module checks the Payaza account endpoint, starts KES mobile-money
collections, verifies collection webhook signatures, and sends KES payouts.
Payout requests do not include X-ProductID.
"""

import base64
import hashlib
import hmac
import json
import logging
import socket
import urllib.error
import urllib.request
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MAIN_ACCOUNTS_PATH = "/payaza-account/api/v1/mainaccounts"
MAIN_ACCOUNT_ENQUIRY_PATH = "/payaza-account/api/v1/mainaccounts/merchant/enquiry/main"
COLLECTION_PATH = "/subsidiary/collections/v1/process-collection"
COLLECTION_STATUS_PATH = "/subsidiary/collections/v1/check-status"
KES_COLLECTION_COUNTRY = "KE"
KES_COLLECTION_CURRENCY = "KES"
# Documented KES example code from Payaza's process-collection reference.
# Safaricom M-Pesa. No other Kenya code is published in that example.
KES_COLLECTION_BANK_CODES = {
    "SAFKEN": "Safaricom",
}
PLACEHOLDER_KES_NUMBER = "254000000000"
REQUEST_TIMEOUT_SECONDS = 20

_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "public_key",
    "secret",
    "secret_key",
    "token",
    "password",
    "key",
}


class PayazaConfigurationError(Exception):
    """Raised when required Payaza settings are missing."""


def payaza_authorization_value(public_key):
    """Build the Payaza Authorization header value from the public key."""
    encoded_key = base64.b64encode(public_key.encode("utf-8")).decode("ascii")
    return f"Payaza {encoded_key}"


def _configured_credentials():
    public_key = str(getattr(settings, "PAYAZA_PUBLIC_KEY", "") or "").strip()
    secret_key = str(getattr(settings, "PAYAZA_SECRET_KEY", "") or "").strip()
    tenant_id = str(getattr(settings, "PAYAZA_TENANT_ID", "") or "").strip() or "test"
    missing = []
    if not public_key:
        missing.append("PAYAZA_PUBLIC_KEY")
    if not secret_key:
        missing.append("PAYAZA_SECRET_KEY")
    if missing:
        raise PayazaConfigurationError(
            "Missing Payaza configuration: " + ", ".join(missing)
        )
    return public_key, secret_key, tenant_id


def _redact(text, secrets):
    cleaned = text or ""
    for secret in secrets:
        if secret and len(secret) >= 6:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned[:500]


def _safe_message(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("message", "response_message", "detail", "error", "status"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return None


def _account_summary(item):
    if not isinstance(item, dict):
        return None
    summary = {
        "name": item.get("account_name") or item.get("accountName") or item.get("name"),
        "currency": item.get("currency") or item.get("currency_code") or item.get("currencyCode"),
        "country": item.get("country") or item.get("country_code") or item.get("countryCode"),
        "status": item.get("status") or item.get("account_status"),
        "type": item.get("account_type") or item.get("type"),
    }
    if not any(summary.values()):
        return None
    return summary


def _find_account_lists(payload):
    lists = []
    if isinstance(payload, list):
        lists.append(payload)
        return lists
    if not isinstance(payload, dict):
        return lists
    for key in ("data", "accounts", "main_accounts", "mainAccounts", "account", "result"):
        value = payload.get(key)
        if isinstance(value, list):
            lists.append(value)
        elif isinstance(value, dict):
            lists.extend(_find_account_lists(value))
    return lists


def _extract_accounts(payload):
    accounts = []
    for candidate in _find_account_lists(payload):
        for item in candidate[:20]:
            summary = _account_summary(item)
            if summary:
                accounts.append(summary)
        if accounts:
            break
    return accounts


def _response_keys(payload):
    if isinstance(payload, dict):
        return [key for key in payload.keys() if str(key).lower() not in _SENSITIVE_KEYS][:20]
    if isinstance(payload, list):
        return ["list"]
    return []


def fetch_main_accounts():
    """Call Payaza's main-accounts endpoint and return a sanitized result."""
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError as exc:
        logger.error("Payaza configuration is incomplete")
        return {
            "success": False,
            "development_only": True,
            "error": "missing_configuration",
            "message": str(exc),
            "http_status": None,
            "accounts": [],
        }

    base_url = str(getattr(settings, "PAYAZA_API_BASE_URL", "https://api.payaza.africa/live")).rstrip("/")
    url = f"{base_url}{MAIN_ACCOUNTS_PATH}"
    # The secret key is required to be configured, but this GET uses only the public key.
    del secret_key
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": payaza_authorization_value(public_key),
            "X-TenantID": tenant_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if settings.DEBUG:
        logger.info("Payaza request method=GET url=%s", url)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status_code = getattr(response, "status", 200)
            raw_body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if settings.DEBUG:
            logger.info("Payaza response http_status=%s", exc.code)
        raw_body = exc.read().decode("utf-8", errors="replace")
        return _http_error_result(exc.code, raw_body, [public_key])
    except (TimeoutError, socket.timeout):
        logger.error("Payaza connection timed out")
        return {
            "success": False,
            "development_only": True,
            "error": "timeout",
            "message": "Payaza request timed out.",
            "http_status": None,
            "accounts": [],
        }
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason).lower():
            logger.error("Payaza connection timed out")
            error_code = "timeout"
            message = "Payaza request timed out."
        else:
            logger.error("Payaza connection failed")
            error_code = "connection_failed"
            message = "Could not connect to Payaza."
        return {
            "success": False,
            "development_only": True,
            "error": error_code,
            "message": message,
            "http_status": None,
            "accounts": [],
        }

    if settings.DEBUG:
        logger.info("Payaza response http_status=%s", status_code)
    return _success_or_invalid_result(status_code, raw_body, [public_key])


def fetch_main_accounts_requests():
    """Development diagnostic that follows Payaza's official requests example.

    Same URL and authentication as fetch_main_accounts(). This does not replace
    the urllib client and does not call any other Payaza path.
    """
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError as exc:
        logger.error("Payaza configuration is incomplete")
        return _requests_transport_result(
            "missing_configuration",
            str(exc),
        )

    base_url = str(getattr(settings, "PAYAZA_API_BASE_URL", "https://api.payaza.africa/live")).rstrip("/")
    url = f"{base_url}{MAIN_ACCOUNTS_PATH}"
    # The secret key is required to be configured, but this GET uses only the public key.
    del secret_key
    headers = {
        "Authorization": payaza_authorization_value(public_key),
        "X-TenantID": tenant_id,
    }
    if settings.DEBUG:
        logger.info("Payaza requests diagnostic method=GET url=%s", url)

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout:
        logger.error("Payaza requests diagnostic timed out")
        return _requests_transport_result("timeout", "Payaza request timed out.")
    except requests.RequestException:
        logger.error("Payaza requests diagnostic connection failed")
        return _requests_transport_result("connection_failed", "Could not connect to Payaza.")

    status_code = response.status_code
    if settings.DEBUG:
        logger.info("Payaza requests diagnostic http_status=%s", status_code)
    raw_body = response.text or ""
    if 200 <= status_code < 300:
        result = _success_or_invalid_result(status_code, raw_body, [public_key])
    else:
        result = _http_error_result(status_code, raw_body, [public_key])
    result["client"] = "requests"
    return result


def fetch_main_account_enquiry():
    """Development check of the account-enquiry path confirmed by Payaza support.

    GET {base}/payaza-account/api/v1/mainaccounts/merchant/enquiry/main
    This does not create a payment or payout, and it does not send the secret key.
    """
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError as exc:
        logger.error("Payaza configuration is incomplete")
        return _enquiry_result(_requests_transport_result(
            "missing_configuration",
            str(exc),
        ))

    base_url = str(getattr(settings, "PAYAZA_API_BASE_URL", "https://api.payaza.africa/live")).rstrip("/")
    url = f"{base_url}{MAIN_ACCOUNT_ENQUIRY_PATH}"
    # The secret key is required to be configured, but this GET uses only the public key.
    del secret_key
    headers = {
        "Authorization": payaza_authorization_value(public_key),
        "X-TenantID": tenant_id,
    }
    if settings.DEBUG:
        logger.info("Payaza account enquiry method=GET url=%s", url)

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout:
        logger.error("Payaza account enquiry timed out")
        return _enquiry_result(_requests_transport_result("timeout", "Payaza request timed out."))
    except requests.RequestException:
        logger.error("Payaza account enquiry connection failed")
        return _enquiry_result(_requests_transport_result("connection_failed", "Could not connect to Payaza."))

    status_code = response.status_code
    if settings.DEBUG:
        logger.info("Payaza account enquiry http_status=%s", status_code)
    raw_body = response.text or ""
    secrets = [public_key]
    if 200 <= status_code < 300:
        result = _success_or_invalid_result(status_code, raw_body, secrets)
    else:
        result = _http_error_result(status_code, raw_body, secrets)
    result["accounts"] = _redact_accounts(result.get("accounts") or [], secrets)
    return _enquiry_result(result)


def _enquiry_result(result):
    result["client"] = "account-enquiry"
    return result


def _redact_accounts(accounts, secrets):
    cleaned = []
    for account in accounts:
        if not isinstance(account, dict):
            continue
        cleaned.append({
            key: _redact(value, secrets) if isinstance(value, str) else value
            for key, value in account.items()
        })
    return cleaned


def _requests_transport_result(error_code, message):
    return {
        "success": False,
        "development_only": True,
        "client": "requests",
        "error": error_code,
        "message": message,
        "http_status": None,
        "accounts": [],
    }


def _parse_json(raw_body):
    try:
        return json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        return None


def _success_or_invalid_result(status_code, raw_body, secrets):
    payload = _parse_json(raw_body)
    if payload is None:
        logger.error("Payaza returned a non-JSON response with status %s", status_code)
        return {
            "success": False,
            "development_only": True,
            "error": "invalid_response",
            "message": "Payaza returned a non-JSON response.",
            "http_status": status_code,
            "accounts": [],
        }

    authenticated = 200 <= status_code < 300
    message = _safe_message(payload)
    return {
        "success": authenticated,
        "development_only": True,
        "error": None if authenticated else "http_error",
        "message": _redact(message, secrets) if message else None,
        "http_status": status_code,
        "payaza_status": payload.get("status") if isinstance(payload, dict) else None,
        "accounts": _extract_accounts(payload),
        "response_keys": _response_keys(payload),
    }


def _http_error_result(status_code, raw_body, secrets):
    payload = _parse_json(raw_body)
    if status_code in (401, 403):
        error_code = "authentication_failed"
        logger.error("Payaza authentication failed with status %s", status_code)
    else:
        error_code = "http_error"
        logger.error("Payaza returned HTTP %s", status_code)

    if payload is None:
        message = "Payaza rejected the request." if error_code == "authentication_failed" else "Payaza returned an error response."
        if raw_body and not raw_body.lstrip().startswith(("{", "[")):
            message = "Payaza returned a non-JSON error response."
            error_code = "invalid_response" if status_code not in (401, 403) else error_code
    else:
        message = _safe_message(payload) or "Payaza rejected the request."

    return {
        "success": False,
        "development_only": True,
        "error": error_code,
        "message": _redact(message, secrets),
        "http_status": status_code,
        "payaza_status": payload.get("status") if isinstance(payload, dict) else None,
        "accounts": [],
    }


def _collection_headers(public_key, tenant_id):
    product_id = str(getattr(settings, "PAYAZA_PRODUCT_ID", "app") or "app")
    return {
        "Authorization": payaza_authorization_value(public_key),
        "X-TenantID": tenant_id,
        "X-ProductID": product_id,
        "Content-Type": "application/json",
    }


def _payaza_base_url():
    return str(getattr(settings, "PAYAZA_API_BASE_URL", "https://api.payaza.africa/live")).rstrip("/")


def kes_customer_number(phone_number):
    """Return a 12-digit 254 number, or None when the stored phone cannot be used."""
    digits = "".join(character for character in str(phone_number or "") if character.isdigit())
    if len(digits) == 12 and digits.startswith("254") and digits != PLACEHOLDER_KES_NUMBER:
        return digits
    return None


def _missing_kes_customer_fields(payment, customer_bank_code):
    client = payment.client
    missing = []
    bank_code = str(customer_bank_code or "").strip().upper()
    if bank_code not in KES_COLLECTION_BANK_CODES:
        missing.append("customer_bank_code")
    if not str(client.first_name or "").strip():
        missing.append("customer_first_name")
    if not str(client.last_name or "").strip():
        missing.append("customer_last_name")
    if not str(client.email or "").strip():
        missing.append("customer_email")
    if not kes_customer_number(client.phone_number):
        missing.append("customer_number")
    return missing


def build_kes_collection_payload(payment, customer_bank_code):
    """Build the documented KES collection body from the payment and its client."""
    missing = _missing_kes_customer_fields(payment, customer_bank_code)
    if missing:
        return None, missing
    client = payment.client
    customer_number = kes_customer_number(client.phone_number)
    description = f"KaziBridge {payment.job.title}".strip()[:120]
    payload = {
        "amount": float(payment.amount.quantize(Decimal("0.01"))),
        "customer_number": customer_number,
        "transaction_reference": payment.transaction_reference,
        "transaction_description": description,
        "customer_bank_code": str(customer_bank_code).strip().upper(),
        "currency_code": KES_COLLECTION_CURRENCY,
        "customer_email": client.email.strip(),
        "customer_first_name": client.first_name.strip(),
        "customer_last_name": client.last_name.strip(),
        "customer_phone_number": customer_number,
        "country_code": KES_COLLECTION_COUNTRY,
    }
    return payload, []


def _collection_outcome(payload):
    """Classify a Payaza collection or status payload.

    completed requires response code 00 and an explicit success status.
    A process-collection response of 09/PENDING is pending, not completed.
    """
    if not isinstance(payload, dict):
        return "unknown"
    code = str(payload.get("response_code") or "").strip()
    status_text = str(
        payload.get("transaction_status") or payload.get("response_message") or ""
    ).strip().lower()
    if code in {"06", "96"} or status_text in {"failed", "transaction failed"}:
        return "failed"
    if code == "00" and status_text in {"completed", "funds received", "success", "successful"}:
        return "completed"
    if code == "09" or status_text in {"pending", "initialized"}:
        return "pending"
    return "unknown"


def _provider_reference(payload, local_reference):
    if not isinstance(payload, dict):
        return None
    for key in ("payment_token", "provider_transaction_reference", "session_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != local_reference:
            return value.strip()[:128]
    echoed = payload.get("transaction_reference")
    if isinstance(echoed, str) and echoed.strip() and echoed.strip() != local_reference:
        return echoed.strip()[:128]
    return None


def _collection_result(**kwargs):
    result = {
        "ok": False,
        "error": None,
        "message": None,
        "http_status": None,
        "initialized": False,
        "outcome": "unknown",
        "provider_transaction_reference": None,
        "response_code": None,
        "response_message": None,
        "transaction_status": None,
    }
    result.update(kwargs)
    return result


def _post_collection(payment, payload, public_key, tenant_id):
    url = f"{_payaza_base_url()}{COLLECTION_PATH}"
    headers = _collection_headers(public_key, tenant_id)
    logger.info(
        "Payaza collection method=POST payment_id=%s transaction_reference=%s url=%s",
        payment.id,
        payment.transaction_reference,
        url,
    )
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout:
        logger.error(
            "Payaza collection timed out payment_id=%s transaction_reference=%s",
            payment.id,
            payment.transaction_reference,
        )
        return _collection_result(error="payaza_unavailable", message="Payaza request timed out.")
    except requests.RequestException:
        logger.error(
            "Payaza collection connection failed payment_id=%s transaction_reference=%s",
            payment.id,
            payment.transaction_reference,
        )
        return _collection_result(error="payaza_unavailable", message="Could not connect to Payaza.")
    return _interpret_collection_response(payment, response, public_key, initialize=True)


def _interpret_collection_response(payment, response, public_key, initialize):
    status_code = response.status_code
    payload = _parse_json(response.text or "")
    logger.info(
        "Payaza collection response payment_id=%s transaction_reference=%s http_status=%s",
        payment.id,
        payment.transaction_reference,
        status_code,
    )
    if payload is None:
        return _collection_result(
            error="payaza_unavailable",
            message="Payaza returned a non-JSON response.",
            http_status=status_code,
        )
    outcome = _collection_outcome(payload)
    message = _safe_message(payload) or payload.get("response_message")
    if isinstance(message, str):
        message = _redact(message, [public_key])
    else:
        message = None
    provider_reference = _provider_reference(payload, payment.transaction_reference)
    response_code = payload.get("response_code")
    transaction_status = payload.get("transaction_status")
    if status_code >= 400 or outcome == "failed":
        return _collection_result(
            error="payaza_rejected",
            message=message or "Payaza rejected the collection request.",
            http_status=status_code,
            outcome="failed",
            response_code=response_code if isinstance(response_code, str) else None,
            response_message=message,
            transaction_status=transaction_status if isinstance(transaction_status, str) else None,
        )
    if initialize:
        initialized = 200 <= status_code < 300 and outcome == "pending"
        if not initialized:
            return _collection_result(
                error="payaza_unavailable",
                message=message or "Payaza did not confirm that the collection was initialized.",
                http_status=status_code,
                outcome=outcome,
                response_code=response_code if isinstance(response_code, str) else None,
                response_message=message,
                transaction_status=transaction_status if isinstance(transaction_status, str) else None,
            )
        return _collection_result(
            ok=True,
            message=message or "Collection initialized.",
            http_status=status_code,
            initialized=True,
            outcome="pending",
            provider_transaction_reference=provider_reference,
            response_code=response_code if isinstance(response_code, str) else None,
            response_message=message,
            transaction_status=transaction_status if isinstance(transaction_status, str) else None,
        )
    return _collection_result(
        ok=200 <= status_code < 300,
        error=None if 200 <= status_code < 300 else "payaza_rejected",
        message=message,
        http_status=status_code,
        outcome=outcome,
        provider_transaction_reference=provider_reference,
        response_code=response_code if isinstance(response_code, str) else None,
        response_message=message,
        transaction_status=transaction_status if isinstance(transaction_status, str) else None,
    )


def start_kes_collection(payment, customer_bank_code):
    """POST a KES collection. The caller decides whether to change local status."""
    if str(payment.currency or "").upper() != KES_COLLECTION_CURRENCY:
        return _collection_result(
            error="payment_not_payable",
            message="Only KES payments can be sent to Payaza collection.",
        )
    payload, missing = build_kes_collection_payload(payment, customer_bank_code)
    if missing:
        return _collection_result(
            error="missing_customer_information",
            message="Missing customer information: " + ", ".join(missing),
        )
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError as exc:
        logger.error("Payaza configuration is incomplete")
        return _collection_result(error="payaza_unavailable", message=str(exc))
    del secret_key
    return _post_collection(payment, payload, public_key, tenant_id)


def fetch_kes_collection_status(payment):
    """GET collection status. This does not change the local payment."""
    if str(payment.currency or "").upper() != KES_COLLECTION_CURRENCY:
        return _collection_result(
            error="payment_not_payable",
            message="Only KES payments can be checked with Payaza collection.",
        )
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError as exc:
        logger.error("Payaza configuration is incomplete")
        return _collection_result(error="payaza_unavailable", message=str(exc))
    del secret_key
    url = f"{_payaza_base_url()}{COLLECTION_STATUS_PATH}"
    headers = _collection_headers(public_key, tenant_id)
    logger.info(
        "Payaza collection status method=GET payment_id=%s transaction_reference=%s url=%s",
        payment.id,
        payment.transaction_reference,
        url,
    )
    try:
        response = requests.get(
            url,
            params={
                "transaction_reference": payment.transaction_reference,
                "country_code": KES_COLLECTION_COUNTRY,
            },
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        logger.error(
            "Payaza collection status timed out payment_id=%s transaction_reference=%s",
            payment.id,
            payment.transaction_reference,
        )
        return _collection_result(error="payaza_unavailable", message="Payaza request timed out.")
    except requests.RequestException:
        logger.error(
            "Payaza collection status connection failed payment_id=%s transaction_reference=%s",
            payment.id,
            payment.transaction_reference,
        )
        return _collection_result(error="payaza_unavailable", message="Could not connect to Payaza.")
    return _interpret_collection_response(payment, response, public_key, initialize=False)


def verify_collection_webhook_signature(raw_body, signature_header):
    """Check the documented x-payaza-signature header.

    Payaza signs the raw webhook body with HMAC-SHA512 using the secret key
    and sends the digest as base64. The secret key is not base64-encoded.
    """
    try:
        _public_key, secret_key, _tenant_id = _configured_credentials()
    except PayazaConfigurationError:
        logger.error("Payaza configuration is incomplete")
        return False
    del _public_key
    if not isinstance(signature_header, str) or not signature_header.strip():
        return False
    if not isinstance(raw_body, (bytes, bytearray)):
        return False
    digest = hmac.new(secret_key.encode("utf-8"), bytes(raw_body), hashlib.sha512).digest()
    expected = base64.b64encode(digest)
    provided = signature_header.strip().encode("ascii", errors="ignore")
    if len(expected) != len(provided):
        return False
    return hmac.compare_digest(expected, provided)


def collection_webhook_merchant_reference(payload):
    """Return the KaziBridge reference from a collection webhook.

    Payaza's collection webhook puts the merchant's own reference in
    merchant_reference. transaction_reference on that payload is Payaza's id.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get("merchant_reference")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def collection_webhook_provider_reference(payload, local_reference):
    """Return a Payaza id from the webhook, never the local KZB reference."""
    if not isinstance(payload, dict):
        return None
    for key in ("session_id", "transaction_reference"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != local_reference:
            return value.strip()[:128]
    return None


TRANSFER_PATH = "/payout-receptor/payout"
TRANSFER_STATUS_PATH = "/payaza-account/api/v1/mainaccounts/transaction/status"
KES_PAYOUT_COUNTRY = "KEN"
PAYOUT_NARRATION = "KaziBridge payout"


def _transfer_headers(public_key, tenant_id):
    """Transfer calls use Authorization and X-TenantID. They do not send X-ProductID."""
    return {
        "Authorization": payaza_authorization_value(public_key),
        "X-TenantID": tenant_id,
        "Content-Type": "application/json",
    }


def payout_country_for_payaza(local_country):
    """Payaza transfer examples use a 3-letter country. Local storage stays 2 letters."""
    if str(local_country or "").strip().upper() == "KE":
        return KES_PAYOUT_COUNTRY
    return None


def _setting_text(name):
    return str(getattr(settings, name, "") or "").strip()


def _payout_configuration():
    """Return payout settings, or a list of missing names. Never return the PIN in errors."""
    values = {
        "transaction_pin": _setting_text("PAYAZA_TRANSACTION_PIN"),
        "account_reference": _setting_text("PAYAZA_KES_ACCOUNT_REFERENCE"),
        "bank_code": _setting_text("PAYAZA_PAYOUT_BANK_CODE"),
        "sender_name": _setting_text("PAYAZA_SENDER_NAME"),
        "sender_phone_number": _setting_text("PAYAZA_SENDER_PHONE"),
        "sender_address": _setting_text("PAYAZA_SENDER_ADDRESS"),
    }
    missing = [name for name, value in values.items() if not value]
    return values, missing


def _freelancer_payout_gaps(payout):
    freelancer = payout.freelancer
    missing = []
    if not str(freelancer.first_name or "").strip():
        missing.append("customer_first_name")
    if not str(freelancer.last_name or "").strip():
        missing.append("customer_last_name")
    if not kes_customer_number(freelancer.phone_number):
        missing.append("account_number")
    return missing


def _pin_value(pin):
    if pin.isdigit() and not pin.startswith("0"):
        return int(pin)
    return pin


def build_kes_payout_payload(payout):
    """Build the documented transfer body. Beneficiaries sit inside service_payload."""
    if str(payout.currency or "").upper() != KES_COLLECTION_CURRENCY:
        return None, "payment_not_payable", "Only KES payouts can be sent to Payaza."
    if payout.payout_method != "MOBILE_MONEY":
        return None, "payment_not_payable", "Only mobile-money payouts can be sent to Payaza."
    country = payout_country_for_payaza(payout.destination_country)
    if country is None:
        return None, "payment_not_payable", "Only a KE payout can be sent as KEN."
    config, missing_config = _payout_configuration()
    if "transaction_pin" in missing_config:
        return None, "missing_transaction_pin", "Payaza transaction PIN is not configured."
    if "account_reference" in missing_config:
        return None, "missing_kes_account_reference", "Payaza KES account reference is not configured."
    if "bank_code" in missing_config:
        return None, "missing_payout_bank_code", "Payaza payout bank code is not configured."
    sender_missing = [name for name in missing_config if name.startswith("sender_")]
    if sender_missing:
        return None, "missing_payout_configuration", "Payaza sender details are not configured."
    freelancer_missing = _freelancer_payout_gaps(payout)
    if freelancer_missing:
        return None, "missing_freelancer_information", "Missing freelancer information: " + ", ".join(freelancer_missing)
    freelancer = payout.freelancer
    amount = float(payout.amount.quantize(Decimal("0.01")))
    account_name = f"{freelancer.first_name.strip()} {freelancer.last_name.strip()}".strip()
    payload = {
        "transaction_type": "mobile_money",
        "service_payload": {
            "payout_amount": amount,
            "transaction_pin": _pin_value(config["transaction_pin"]),
            "account_reference": config["account_reference"],
            "currency": KES_COLLECTION_CURRENCY,
            "country": country,
            "payout_beneficiaries": [
                {
                    "credit_amount": amount,
                    "account_number": kes_customer_number(freelancer.phone_number),
                    "account_name": account_name,
                    "bank_code": config["bank_code"],
                    "narration": PAYOUT_NARRATION,
                    "transaction_reference": payout.transaction_reference,
                    "sender": {
                        "sender_name": config["sender_name"],
                        "sender_phone_number": config["sender_phone_number"],
                        "sender_address": config["sender_address"],
                    },
                }
            ],
        },
    }
    return payload, None, None


def _transfer_message(payload):
    if not isinstance(payload, dict):
        return None
    content = payload.get("response_content")
    if isinstance(content, dict):
        for key in ("response_description", "message"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:500]
    return _safe_message(payload)


def _transfer_provider_reference(payload, local_reference):
    if not isinstance(payload, dict):
        return None
    content = payload.get("response_content")
    data = payload.get("data")
    sources = [payload]
    if isinstance(content, dict):
        sources.append(content)
    if isinstance(data, dict):
        sources.append(data)
    for source in sources:
        for key in ("session_id", "batch_reference", "provider_transaction_reference"):
            value = source.get(key)
            if isinstance(value, str) and value.strip() and value.strip() != local_reference:
                return value.strip()[:128]
    return None


def _transfer_result(**kwargs):
    result = {
        "ok": False,
        "error": None,
        "message": None,
        "http_status": None,
        "outcome": "unknown",
        "provider_transaction_reference": None,
        "response_code": None,
        "response_status": None,
    }
    result.update(kwargs)
    return result


def _classify_transfer_problem(message, payload):
    text = (message or "").lower()
    resp_code = ""
    if isinstance(payload, dict) and payload.get("resp_code") is not None:
        resp_code = str(payload.get("resp_code"))
    if "insufficient balance" in text:
        return "insufficient_balance"
    if "already exists" in text or resp_code == "X03":
        return "duplicate_reference"
    return None


def _initiation_outcome(payload):
    if not isinstance(payload, dict):
        return "unknown", None
    content = payload.get("response_content") if isinstance(payload.get("response_content"), dict) else {}
    code = str(content.get("transaction_status") or payload.get("resp_code") or "").strip()
    response_status = str(content.get("response_status") or "").strip()
    if code == "09" and response_status == "TRANSACTION_INITIATED":
        return "initiated", response_status
    return "unknown", response_status or None


def _status_outcome(payload):
    if not isinstance(payload, dict):
        return "unknown", None, None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    status_text = str(data.get("transactionStatus") or data.get("transaction_status") or "").strip()
    code = str(data.get("responseCode") or data.get("response_code") or "").strip()
    normalized = status_text.upper()
    if normalized == "NIP_FAILURE":
        return "failed", code or None, status_text
    if normalized == "NIP_SUCCESS" and code == "00":
        return "paid", code, status_text
    if normalized in {"NIP_PENDING", "ESCROW_SUCCESS", "TRANSACTION_INITIATED"}:
        return "processing", code or None, status_text
    return "unknown", code or None, status_text or None


def _interpret_transfer_response(payout, response, public_key, pin, status_check):
    status_code = response.status_code
    payload = _parse_json(response.text or "")
    logger.info(
        "Payaza payout response payout_id=%s transaction_reference=%s http_status=%s",
        payout.id,
        payout.transaction_reference,
        status_code,
    )
    secrets = [public_key, pin]
    if payload is None:
        return _transfer_result(
            error="payaza_unavailable",
            message="Payaza returned a non-JSON response.",
            http_status=status_code,
        )
    message = _transfer_message(payload)
    if isinstance(message, str):
        message = _redact(message, secrets)
    problem = _classify_transfer_problem(message, payload)
    provider_reference = _transfer_provider_reference(payload, payout.transaction_reference)
    if problem:
        return _transfer_result(
            error=problem,
            message=message or "Payaza rejected the payout.",
            http_status=status_code,
            outcome=problem,
            provider_transaction_reference=provider_reference,
        )
    if status_code >= 400:
        return _transfer_result(
            error="payaza_rejected",
            message=message or "Payaza rejected the payout.",
            http_status=status_code,
            outcome="failed",
        )
    if status_check:
        outcome, code, response_status = _status_outcome(payload)
        if outcome == "unknown":
            return _transfer_result(
                error="payaza_unavailable",
                message=message or "Payaza returned an unclear payout status.",
                http_status=status_code,
                outcome="unknown",
                response_code=code,
                response_status=response_status,
            )
        return _transfer_result(
            ok=True,
            message=message,
            http_status=status_code,
            outcome=outcome,
            provider_transaction_reference=provider_reference,
            response_code=code,
            response_status=response_status,
        )
    outcome, response_status = _initiation_outcome(payload)
    if outcome != "initiated":
        return _transfer_result(
            error="payaza_unavailable",
            message=message or "Payaza did not confirm that the payout was initiated.",
            http_status=status_code,
            outcome="unknown",
            response_status=response_status,
        )
    return _transfer_result(
        ok=True,
        message=message or "Payout initiated.",
        http_status=status_code,
        outcome="initiated",
        provider_transaction_reference=provider_reference,
        response_code="09",
        response_status=response_status,
    )


def start_kes_payout(payout):
    """POST one KES mobile-money transfer. The caller changes local status."""
    payload, error, message = build_kes_payout_payload(payout)
    if error:
        return _transfer_result(error=error, message=message)
    pin = str(payload["service_payload"]["transaction_pin"])
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError:
        logger.error("Payaza configuration is incomplete")
        return _transfer_result(error="payaza_unavailable", message="Payaza configuration is incomplete.")
    del secret_key
    url = f"{_payaza_base_url()}{TRANSFER_PATH}"
    headers = _transfer_headers(public_key, tenant_id)
    logger.info(
        "Payaza payout method=POST payout_id=%s transaction_reference=%s url=%s",
        payout.id,
        payout.transaction_reference,
        url,
    )
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.Timeout:
        logger.error(
            "Payaza payout timed out payout_id=%s transaction_reference=%s",
            payout.id,
            payout.transaction_reference,
        )
        return _transfer_result(error="payaza_unavailable", message="Payaza request timed out.")
    except requests.RequestException:
        logger.error(
            "Payaza payout connection failed payout_id=%s transaction_reference=%s",
            payout.id,
            payout.transaction_reference,
        )
        return _transfer_result(error="payaza_unavailable", message="Could not connect to Payaza.")
    return _interpret_transfer_response(payout, response, public_key, pin, status_check=False)


def fetch_kes_payout_status(payout):
    """GET transfer status. This does not use the collection status endpoint."""
    try:
        public_key, secret_key, tenant_id = _configured_credentials()
    except PayazaConfigurationError:
        logger.error("Payaza configuration is incomplete")
        return _transfer_result(error="payaza_unavailable", message="Payaza configuration is incomplete.")
    del secret_key
    pin = _setting_text("PAYAZA_TRANSACTION_PIN")
    url = f"{_payaza_base_url()}{TRANSFER_STATUS_PATH}"
    headers = _transfer_headers(public_key, tenant_id)
    logger.info(
        "Payaza payout status method=GET payout_id=%s transaction_reference=%s url=%s",
        payout.id,
        payout.transaction_reference,
        url,
    )
    try:
        response = requests.get(
            url,
            params={"transaction_reference": payout.transaction_reference},
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        logger.error(
            "Payaza payout status timed out payout_id=%s transaction_reference=%s",
            payout.id,
            payout.transaction_reference,
        )
        return _transfer_result(error="payaza_unavailable", message="Payaza request timed out.")
    except requests.RequestException:
        logger.error(
            "Payaza payout status connection failed payout_id=%s transaction_reference=%s",
            payout.id,
            payout.transaction_reference,
        )
        return _transfer_result(error="payaza_unavailable", message="Could not connect to Payaza.")
    return _interpret_transfer_response(payout, response, public_key, pin, status_check=True)


def payout_webhook_reference(payload):
    """Return the merchant payout reference from a transfer webhook.

    Payaza's transfer webhook puts that reference in transaction_reference.
    """
    if not isinstance(payload, dict):
        return None
    value = payload.get("transaction_reference")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
