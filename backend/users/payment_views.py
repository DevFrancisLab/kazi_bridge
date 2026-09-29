"""Payment and payout foundation, plus KES collection through Payaza.

Creating a payment does not call Payaza. POST /api/payments/{id}/payaza/ does.
A collection prompt moves the payment to PAYMENT_PROCESSING only.
PAYMENT_RECEIVED requires a verified Payaza status result:
response code 00 with transaction status Completed, Funds Received, success,
or successful. The collection webhook confirms that result server-side.
Staff can still move statuses through the existing PATCH endpoints.
"""

import json
import logging
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bid, Earnings, Job, Payment, Payout
from .payaza import (
    collection_webhook_merchant_reference,
    collection_webhook_provider_reference,
    fetch_kes_collection_status,
    fetch_kes_payout_status,
    payout_webhook_reference,
    start_kes_collection,
    start_kes_payout,
    verify_collection_webhook_signature,
)

logger = logging.getLogger(__name__)
from .serializers import (
    PaymentSerializer,
    PaymentStatusSerializer,
    PayoutSerializer,
    PayoutStatusSerializer,
)

PAYABLE_JOB_STATUSES = ('IN_PROGRESS', 'COMPLETED')
COUNTRY_CODE = re.compile(r'^[A-Z]{2}$')
CURRENCY_CODE = re.compile(r'^[A-Z]{3}$')


def _party_payments(user):
    return Payment.objects.filter(Q(client=user) | Q(freelancer=user))


def _party_payouts(user):
    return Payout.objects.filter(Q(payment__client=user) | Q(freelancer=user))


class PaymentListCreateView(generics.ListCreateAPIView):
    """List the caller's payments, or create one for an accepted job they own."""

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return _party_payments(self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if request.user.role != 'CLIENT':
            raise PermissionDenied('Only the client who owns the job can create its payment.')

        job_id = request.data.get('job')
        if not job_id:
            raise ValidationError({'job': 'A job is required.'})
        job = get_object_or_404(Job, pk=job_id)
        if job.created_by_id != request.user.id:
            raise PermissionDenied('Only the client who owns the job can create its payment.')
        if job.status not in PAYABLE_JOB_STATUSES:
            raise ValidationError(
                {'job': 'Payment can only be created after a bid has been accepted.'}
            )

        accepted_bids = list(Bid.objects.filter(job=job, status='ACCEPTED'))
        if len(accepted_bids) != 1:
            raise ValidationError({'job': 'Payment requires exactly one accepted bid.'})
        accepted_bid = accepted_bids[0]
        if Payment.objects.filter(job=job, status__in=Payment.ACTIVE_STATUSES).exists():
            raise ValidationError({'job': 'An active payment already exists for this job.'})

        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    job=job,
                    client=request.user,
                    freelancer=accepted_bid.freelancer,
                    amount=accepted_bid.amount,
                    currency=Payment.DEFAULT_CURRENCY,
                    status=Payment.PAYMENT_PENDING,
                )
        except IntegrityError:
            raise ValidationError({'job': 'An active payment already exists for this job.'})

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve a payment, or apply a staff-only test status transition.

    Status changes here are a development mechanism. They do not create a
    Payaza transaction. Payaza webhook or status handling will confirm
    PAYMENT_RECEIVED once that integration exists.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return PaymentStatusSerializer
        return PaymentSerializer

    def get_queryset(self):
        return _party_payments(self.request.user)

    def get_object(self):
        if self.request.method == 'PATCH':
            return get_object_or_404(Payment, pk=self.kwargs['pk'])
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    def patch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied(
                'Payment status is not confirmed by the client. '
                'Payaza status handling will confirm receipt later.'
            )
        return self.partial_update(request, *args, **kwargs)


class PayoutListCreateView(generics.ListCreateAPIView):
    """List the caller's payouts, or create a pending payout for a received payment."""

    permission_classes = [IsAuthenticated]
    serializer_class = PayoutSerializer

    def get_queryset(self):
        return _party_payouts(self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        payment_id = request.data.get('payment')
        if not payment_id:
            raise ValidationError({'payment': 'A payment is required.'})
        payment = get_object_or_404(Payment, pk=payment_id)
        if request.user.id not in (payment.client_id, payment.freelancer_id):
            raise PermissionDenied('You can only create a payout for your own payment.')
        if payment.status != Payment.PAYMENT_RECEIVED:
            raise ValidationError(
                {'payment': 'A payout can only be created after the payment is received.'}
            )
        if Payout.objects.filter(payment=payment, status__in=Payout.ACTIVE_STATUSES).exists():
            raise ValidationError({'payment': 'An active payout already exists for this payment.'})

        destination_country = str(request.data.get('destination_country') or '').strip().upper()
        destination_currency = str(request.data.get('destination_currency') or '').strip().upper()
        payout_method = str(request.data.get('payout_method') or '').strip().upper()
        destination_reference = str(request.data.get('destination_reference') or '').strip()
        errors = {}
        if not COUNTRY_CODE.match(destination_country):
            errors['destination_country'] = 'Use a two-letter country code.'
        if not CURRENCY_CODE.match(destination_currency):
            errors['destination_currency'] = 'Use a three-letter currency code.'
        if payout_method not in dict(Payout.METHOD_CHOICES):
            errors['payout_method'] = 'Use a supported payout method.'
        if len(destination_reference) > 100:
            errors['destination_reference'] = 'Destination reference is too long.'
        if errors:
            raise ValidationError(errors)

        try:
            with transaction.atomic():
                payout = Payout.objects.create(
                    payment=payment,
                    freelancer=payment.freelancer,
                    amount=payment.amount,
                    currency=payment.currency,
                    destination_country=destination_country,
                    destination_currency=destination_currency,
                    payout_method=payout_method,
                    destination_reference=destination_reference,
                    status=Payout.PAYOUT_PENDING,
                )
                earning = Earnings.objects.filter(payment=payment).select_related('payout').first()
                previous = earning.payout if earning else None
                replaceable = previous is None or previous.status in {
                    Payout.PAYOUT_FAILED,
                    Payout.PAYOUT_CANCELLED,
                }
                if earning and replaceable:
                    earning.payout = payout
                    earning.save(update_fields=['payout'])
        except IntegrityError:
            raise ValidationError({'payment': 'An active payout already exists for this payment.'})

        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class PayoutDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve a payout, or apply a staff-only test status transition.

    Creating or updating a payout does not transfer money. Payaza status
    handling will confirm PAYOUT_PAID once that integration exists.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return PayoutStatusSerializer
        return PayoutSerializer

    def get_queryset(self):
        return _party_payouts(self.request.user)

    def get_object(self):
        if self.request.method == 'PATCH':
            return get_object_or_404(Payout, pk=self.kwargs['pk'])
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    def patch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied(
                'Payout status is not confirmed from this account. '
                'Payaza status handling will confirm a paid payout later.'
            )
        return self.partial_update(request, *args, **kwargs)


def _error_response(error, message, http_status):
    return Response({"error": error, "message": message}, status=http_status)


def _payaza_http_status(result):
    if result.get("error") == "payaza_rejected":
        return status.HTTP_502_BAD_GATEWAY
    if result.get("message") == "Payaza request timed out.":
        return status.HTTP_504_GATEWAY_TIMEOUT
    if result.get("error") == "payaza_unavailable":
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_400_BAD_REQUEST


class PaymentPayazaCollectionView(APIView):
    """Start a Payaza KES collection for a pending payment.

    A successful response means Payaza initialized or prompted the collection.
    It does not mean the customer has paid, so the payment stays out of
    PAYMENT_RECEIVED.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        payment = _party_payments(request.user).select_related("client", "job").filter(pk=pk).first()
        if payment is None:
            raise Http404
        if payment.client_id != request.user.id:
            raise PermissionDenied("Only the client who owns this payment can start collection.")
        if str(payment.currency or "").upper() != "KES":
            return _error_response(
                "payment_not_payable",
                "Only KES payments can be sent to Payaza collection.",
                status.HTTP_400_BAD_REQUEST,
            )
        if payment.provider_transaction_reference and payment.status == Payment.PAYMENT_PENDING:
            return Response(
                {
                    "error": None,
                    "message": "Payaza collection was already initialized for this payment.",
                    "initialized": True,
                    "payment": PaymentSerializer(payment).data,
                },
                status=status.HTTP_200_OK,
            )
        if payment.status != Payment.PAYMENT_PENDING:
            return _error_response(
                "invalid_payment_state",
                "Only a pending payment can start Payaza collection.",
                status.HTTP_400_BAD_REQUEST,
            )

        result = start_kes_collection(payment, request.data.get("customer_bank_code"))
        if not result["initialized"]:
            return _error_response(result["error"], result["message"], _payaza_http_status(result))

        if result["provider_transaction_reference"]:
            payment.provider_transaction_reference = result["provider_transaction_reference"]
            payment.save(update_fields=["provider_transaction_reference", "updated_at"])
        payment.transition_to(Payment.PAYMENT_PROCESSING)
        payment.refresh_from_db()
        return Response(
            {
                "error": None,
                "message": result["message"],
                "initialized": True,
                "payaza_response_code": result["response_code"],
                "payaza_response_message": result["response_message"],
                "payment": PaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )


class PaymentPayazaStatusView(APIView):
    """Read Payaza collection status for a payment the caller can already see.

    Local status changes only while the payment is PAYMENT_PROCESSING:
    response code 00 and transaction status Completed or Funds Received
    become PAYMENT_RECEIVED. Response code 06 or 96, or transaction status
    Failed, becomes PAYMENT_FAILED. Initialized, Pending, and code 09 do not
    change the local payment.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payment = _party_payments(request.user).filter(pk=pk).first()
        if payment is None:
            raise Http404
        if str(payment.currency or "").upper() != "KES":
            return _error_response(
                "payment_not_payable",
                "Only KES payments can be checked with Payaza collection.",
                status.HTTP_400_BAD_REQUEST,
            )
        result = fetch_kes_collection_status(payment)
        if result["error"]:
            return _error_response(result["error"], result["message"], _payaza_http_status(result))

        changed = False
        if payment.status == Payment.PAYMENT_PROCESSING and result["outcome"] == "completed":
            payment.transition_to(Payment.PAYMENT_RECEIVED)
            changed = True
        elif payment.status == Payment.PAYMENT_PROCESSING and result["outcome"] == "failed":
            payment.transition_to(Payment.PAYMENT_FAILED)
            changed = True
        if result["provider_transaction_reference"] and not payment.provider_transaction_reference:
            payment.provider_transaction_reference = result["provider_transaction_reference"]
            payment.save(update_fields=["provider_transaction_reference", "updated_at"])
        payment.refresh_from_db()
        return Response(
            {
                "error": None,
                "payaza_response_code": result["response_code"],
                "payaza_transaction_status": result["transaction_status"],
                "local_status_changed": changed,
                "payment": PaymentSerializer(payment).data,
            },
            status=status.HTTP_200_OK,
        )


def _remember_provider_reference(payment, *candidates):
    """Store the first real Payaza id. Never replace one that is already stored."""
    if payment.provider_transaction_reference:
        return
    local_reference = payment.transaction_reference
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip() and candidate.strip() != local_reference:
            payment.provider_transaction_reference = candidate.strip()[:128]
            payment.save(update_fields=["provider_transaction_reference", "updated_at"])
            return


def _apply_verified_collection_status(payment, outcome):
    """Apply a verified Payaza outcome. Only PROCESSING can move."""
    if payment.status != Payment.PAYMENT_PROCESSING:
        return False
    if outcome == "completed":
        payment.transition_to(Payment.PAYMENT_RECEIVED)
        return True
    if outcome == "failed":
        payment.transition_to(Payment.PAYMENT_FAILED)
        return True
    return False


class PaymentPayazaWebhookView(APIView):
    """Receive a Payaza collection webhook and confirm it with a status query.

    Payaza signs the raw body in x-payaza-signature (HMAC-SHA512, base64,
    secret key). The webhook status string is not enough to mark a payment
    received. The local change uses the existing KES status check.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not verify_collection_webhook_signature(
            request.body,
            request.headers.get("x-payaza-signature"),
        ):
            logger.error("Payaza webhook rejected: invalid signature")
            return _error_response(
                "invalid_signature",
                "Webhook signature could not be verified.",
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.error("Payaza webhook rejected: malformed JSON")
            return _error_response(
                "invalid_webhook",
                "Webhook body is not valid JSON.",
                status.HTTP_400_BAD_REQUEST,
            )
        merchant_reference = collection_webhook_merchant_reference(payload)
        if not merchant_reference:
            logger.error("Payaza webhook rejected: missing merchant_reference")
            return _error_response(
                "missing_transaction_reference",
                "Webhook is missing merchant_reference.",
                status.HTTP_400_BAD_REQUEST,
            )
        payment = Payment.objects.filter(transaction_reference=merchant_reference).first()
        if payment is None:
            logger.info(
                "Payaza webhook unknown transaction_reference=%s",
                merchant_reference,
            )
            return _error_response(
                "unknown_transaction_reference",
                "No payment matches this transaction reference.",
                status.HTTP_404_NOT_FOUND,
            )

        webhook_provider_reference = collection_webhook_provider_reference(
            payload,
            payment.transaction_reference,
        )
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment.pk)
            _remember_provider_reference(locked, webhook_provider_reference)

        result = fetch_kes_collection_status(payment)
        if result["error"]:
            logger.error(
                "Payaza webhook verification failed transaction_reference=%s error=%s",
                payment.transaction_reference,
                result["error"],
            )
            return _error_response(result["error"], result["message"], _payaza_http_status(result))

        changed = False
        with transaction.atomic():
            locked = Payment.objects.select_for_update().get(pk=payment.pk)
            _remember_provider_reference(
                locked,
                webhook_provider_reference,
                result["provider_transaction_reference"],
            )
            try:
                changed = _apply_verified_collection_status(locked, result["outcome"])
            except DjangoValidationError:
                logger.error(
                    "Payaza webhook skipped invalid transition transaction_reference=%s outcome=%s local_status=%s",
                    locked.transaction_reference,
                    result["outcome"],
                    locked.status,
                )
                changed = False
            locked.refresh_from_db()

        logger.info(
            "Payaza webhook transaction_reference=%s provider_reference=%s verified_outcome=%s local_status=%s changed=%s",
            locked.transaction_reference,
            locked.provider_transaction_reference or "",
            result["outcome"],
            locked.status,
            changed,
        )
        return Response(
            {
                "acknowledged": True,
                "error": None,
                "local_status_changed": changed,
                "payment_status": locked.status,
            },
            status=status.HTTP_200_OK,
        )


def _payout_error_status(result):
    if result.get("message") == "Payaza request timed out.":
        return status.HTTP_504_GATEWAY_TIMEOUT
    if result.get("error") in {
        "payaza_rejected",
        "payaza_unavailable",
        "insufficient_balance",
        "duplicate_reference",
    }:
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_400_BAD_REQUEST


def _apply_verified_payout_status(payout, outcome):
    """Apply a verified transfer result. ESCROW_SUCCESS and pending do not pay out."""
    if outcome == "paid" and payout.status == Payout.PAYOUT_PROCESSING:
        payout.transition_to(Payout.PAYOUT_PAID)
        return True
    if outcome == "failed" and payout.status in {Payout.PAYOUT_PENDING, Payout.PAYOUT_PROCESSING}:
        payout.transition_to(Payout.PAYOUT_FAILED)
        return True
    return False


class PayoutPayazaTransferView(APIView):
    """Start one Payaza KES mobile-money transfer for a pending payout.

    TRANSACTION_INITIATED moves the payout to PAYOUT_PROCESSING. It does not
    mean the freelancer has been paid.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        payout = _party_payouts(request.user).select_related(
            "payment", "freelancer"
        ).filter(pk=pk).first()
        if payout is None:
            raise Http404
        if payout.payment.status != Payment.PAYMENT_RECEIVED:
            return _error_response(
                "invalid_payout_state",
                "A payout can only be sent after the payment is received.",
                status.HTTP_400_BAD_REQUEST,
            )
        if payout.provider_transaction_reference and payout.status == Payout.PAYOUT_PENDING:
            return Response(
                {
                    "error": None,
                    "message": "Payaza payout was already initialized for this payout.",
                    "initialized": True,
                    "payout": PayoutSerializer(payout).data,
                },
                status=status.HTTP_200_OK,
            )
        if payout.status != Payout.PAYOUT_PENDING:
            return _error_response(
                "invalid_payout_state",
                "Only a pending payout can be sent to Payaza.",
                status.HTTP_400_BAD_REQUEST,
            )

        result = start_kes_payout(payout)
        if result["outcome"] != "initiated":
            return _error_response(result["error"], result["message"], _payout_error_status(result))

        if result["provider_transaction_reference"]:
            _remember_provider_reference(payout, result["provider_transaction_reference"])
        payout.transition_to(Payout.PAYOUT_PROCESSING)
        payout.refresh_from_db()
        return Response(
            {
                "error": None,
                "message": result["message"],
                "initialized": True,
                "payaza_response_code": result["response_code"],
                "payaza_response_status": result["response_status"],
                "payout": PayoutSerializer(payout).data,
            },
            status=status.HTTP_200_OK,
        )


class PayoutPayazaStatusView(APIView):
    """Read Payaza transfer status for a payout the caller can already see.

    NIP_SUCCESS with code 00 becomes PAYOUT_PAID. NIP_FAILURE becomes
    PAYOUT_FAILED. NIP_PENDING, ESCROW_SUCCESS, and TRANSACTION_INITIATED do
    not mark the payout paid.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        payout = _party_payouts(request.user).filter(pk=pk).first()
        if payout is None:
            raise Http404
        result = fetch_kes_payout_status(payout)
        if result["error"]:
            return _error_response(result["error"], result["message"], _payout_error_status(result))

        changed = False
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(pk=payout.pk)
            _remember_provider_reference(locked, result["provider_transaction_reference"])
            try:
                changed = _apply_verified_payout_status(locked, result["outcome"])
            except DjangoValidationError:
                changed = False
            locked.refresh_from_db()
        return Response(
            {
                "error": None,
                "payaza_response_code": result["response_code"],
                "payaza_transaction_status": result["response_status"],
                "local_status_changed": changed,
                "payout": PayoutSerializer(locked).data,
            },
            status=status.HTTP_200_OK,
        )


class PayoutPayazaWebhookView(APIView):
    """Receive a Payaza transfer webhook and confirm it with the transfer status API.

    This is separate from collection confirmation. An unknown reference does
    not create a payout.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not verify_collection_webhook_signature(
            request.body,
            request.headers.get("x-payaza-signature"),
        ):
            logger.error("Payaza payout webhook rejected: invalid signature")
            return _error_response(
                "invalid_signature",
                "Webhook signature could not be verified.",
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.error("Payaza payout webhook rejected: malformed JSON")
            return _error_response(
                "invalid_webhook",
                "Webhook body is not valid JSON.",
                status.HTTP_400_BAD_REQUEST,
            )
        reference = payout_webhook_reference(payload)
        if not reference:
            logger.error("Payaza payout webhook rejected: missing transaction_reference")
            return _error_response(
                "missing_transaction_reference",
                "Webhook is missing transaction_reference.",
                status.HTTP_400_BAD_REQUEST,
            )
        payout = Payout.objects.filter(transaction_reference=reference).first()
        if payout is None:
            logger.info("Payaza payout webhook unknown transaction_reference=%s", reference)
            return _error_response(
                "unknown_transaction_reference",
                "No payout matches this transaction reference.",
                status.HTTP_404_NOT_FOUND,
            )

        webhook_provider_reference = collection_webhook_provider_reference(
            payload,
            payout.transaction_reference,
        )
        result = fetch_kes_payout_status(payout)
        if result["error"]:
            logger.error(
                "Payaza payout webhook verification failed transaction_reference=%s error=%s",
                payout.transaction_reference,
                result["error"],
            )
            return _error_response(result["error"], result["message"], _payout_error_status(result))

        changed = False
        with transaction.atomic():
            locked = Payout.objects.select_for_update().get(pk=payout.pk)
            _remember_provider_reference(
                locked,
                webhook_provider_reference,
                result["provider_transaction_reference"],
            )
            try:
                changed = _apply_verified_payout_status(locked, result["outcome"])
            except DjangoValidationError:
                changed = False
            locked.refresh_from_db()
        logger.info(
            "Payaza payout webhook transaction_reference=%s provider_reference=%s verified_outcome=%s local_status=%s changed=%s",
            locked.transaction_reference,
            locked.provider_transaction_reference or "",
            result["outcome"],
            locked.status,
            changed,
        )
        return Response(
            {
                "acknowledged": True,
                "error": None,
                "local_status_changed": changed,
                "payout_status": locked.status,
            },
            status=status.HTTP_200_OK,
        )
