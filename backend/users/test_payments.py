import re
from datetime import date
from decimal import Decimal

from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Bid, Earnings, Job, Payment, Payout, Task, User

PAYMENT_REFERENCE = re.compile(r'^KZB-\d{8}-[A-F0-9]{8}$')
PAYOUT_REFERENCE = re.compile(r'^KZB-PAYOUT-[A-F0-9]{12}$')


def _auth_client(user):
    client = APIClient()
    access = RefreshToken.for_user(user).access_token
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    return client


def _user(username, role, staff=False):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='test-pass-123',
        role=role,
        first_name=username,
    )
    if staff:
        user.is_staff = True
        user.save(update_fields=['is_staff'])
    return user


class PaymentAPIMixin:
    def setUp(self):
        super().setUp()
        self.client_user = _user('client', 'CLIENT')
        self.other_client = _user('other-client', 'CLIENT')
        self.freelancer = _user('freelancer', 'FREELANCER')
        self.other_freelancer = _user('other-freelancer', 'FREELANCER')
        self.staff = _user('staff', 'CLIENT', staff=True)
        self.client_api = _auth_client(self.client_user)
        self.other_client_api = _auth_client(self.other_client)
        self.freelancer_api = _auth_client(self.freelancer)
        self.other_freelancer_api = _auth_client(self.other_freelancer)
        self.staff_api = _auth_client(self.staff)
        self.job, self.bid = self._accepted_job(self.client_user, self.freelancer, Decimal('110000.00'))

    def _accepted_job(self, client, freelancer, amount, status='IN_PROGRESS'):
        job = Job.objects.create(
            title='Cross-border design',
            description='Design work',
            budget=Decimal('120000.00'),
            deadline=date(2026, 10, 30),
            created_by=client,
            status=status,
        )
        bid_status = 'ACCEPTED' if status in ('IN_PROGRESS', 'COMPLETED') else 'PENDING'
        bid = Bid.objects.create(
            job=job,
            freelancer=freelancer,
            amount=amount,
            proposal='I can do this work.',
            status=bid_status,
        )
        return job, bid

    def _create_payment(self, api=None, job=None, **extra):
        payload = {'job': (job or self.job).id}
        payload.update(extra)
        return (api or self.client_api).post(reverse('payments'), payload, format='json')


class PaymentFoundationTests(PaymentAPIMixin, TestCase):
    def test_client_creates_payment_from_accepted_bid(self):
        response = self._create_payment(
            amount='-5.00',
            client=self.other_client.id,
            freelancer=self.other_freelancer.id,
            transaction_reference='CLIENT-SUPPLIED',
            currency='USD',
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get(pk=response.data['id'])
        self.assertEqual(payment.client, self.client_user)
        self.assertEqual(payment.freelancer, self.freelancer)
        self.assertEqual(payment.amount, self.bid.amount)
        self.assertEqual(payment.currency, 'KES')
        self.assertEqual(payment.status, Payment.PAYMENT_PENDING)
        self.assertIsNone(payment.provider_transaction_reference)
        self.assertRegex(payment.transaction_reference, PAYMENT_REFERENCE)
        self.assertNotEqual(payment.transaction_reference, 'CLIENT-SUPPLIED')
        self.assertEqual(response.data['amount'], '110000.00')
        self.assertEqual(response.data['transaction_reference'], payment.transaction_reference)
        self.assertIsNone(response.data['provider_transaction_reference'])

    def test_other_client_and_freelancer_cannot_create_payment(self):
        other = self._create_payment(api=self.other_client_api)
        freelancer = self._create_payment(api=self.freelancer_api)
        anonymous = APIClient().post(reverse('payments'), {'job': self.job.id}, format='json')

        self.assertEqual(other.status_code, 403)
        self.assertEqual(freelancer.status_code, 403)
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(Payment.objects.count(), 0)

    def test_payment_requires_an_accepted_bid_and_accepted_job_state(self):
        open_job = Job.objects.create(
            title='Open role',
            description='Still hiring',
            budget=Decimal('500.00'),
            deadline=date(2026, 11, 1),
            created_by=self.client_user,
            status='OPEN',
        )
        Bid.objects.create(
            job=open_job,
            freelancer=self.freelancer,
            amount=Decimal('400.00'),
            proposal='Pending proposal',
            status='PENDING',
        )
        in_progress = Job.objects.create(
            title='No accepted bid',
            description='Missing bid',
            budget=Decimal('500.00'),
            deadline=date(2026, 11, 1),
            created_by=self.client_user,
            status='IN_PROGRESS',
        )

        open_response = self._create_payment(job=open_job)
        missing_bid = self._create_payment(job=in_progress)

        self.assertEqual(open_response.status_code, 400)
        self.assertEqual(missing_bid.status_code, 400)
        self.assertEqual(Payment.objects.count(), 0)

    def test_duplicate_active_payment_is_rejected_and_failed_payment_can_be_replaced(self):
        first = self._create_payment()
        duplicate = self._create_payment()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Payment.objects.filter(job=self.job).count(), 1)

        failed = self.staff_api.patch(
            reverse('payment-detail', args=[first.data['id']]),
            {'status': Payment.PAYMENT_FAILED},
            format='json',
        )
        self.assertEqual(failed.status_code, 200)
        replacement = self._create_payment()
        self.assertEqual(replacement.status_code, 201)
        self.assertEqual(Payment.objects.filter(job=self.job).count(), 2)

    def test_transaction_references_are_unique(self):
        first = Payment.objects.create(
            job=self.job,
            client=self.client_user,
            freelancer=self.freelancer,
            amount=self.bid.amount,
            currency='KES',
        )
        other_job, _bid = self._accepted_job(
            self.other_client,
            self.other_freelancer,
            Decimal('2500.00'),
        )
        second = Payment.objects.create(
            job=other_job,
            client=self.other_client,
            freelancer=self.other_freelancer,
            amount=Decimal('2500.00'),
            currency='KES',
        )
        self.assertNotEqual(first.transaction_reference, second.transaction_reference)
        second.transaction_reference = first.transaction_reference
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                second.save()

    def test_negative_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            Payment.objects.create(
                job=self.job,
                client=self.client_user,
                freelancer=self.freelancer,
                amount=Decimal('-10.00'),
                currency='KES',
            )
        self.assertEqual(Payment.objects.count(), 0)

    def test_status_transitions_and_empty_provider_reference(self):
        created = self._create_payment()
        payment_id = created.data['id']
        detail = reverse('payment-detail', args=[payment_id])

        skipped = self.staff_api.patch(detail, {'status': Payment.PAYMENT_RECEIVED}, format='json')
        forbidden = self.client_api.patch(detail, {'status': Payment.PAYMENT_PROCESSING}, format='json')
        processing = self.staff_api.patch(
            detail,
            {
                'status': Payment.PAYMENT_PROCESSING,
                'provider_transaction_reference': 'fake-payaza-id',
                'amount': '1.00',
            },
            format='json',
        )
        received = self.staff_api.patch(detail, {'status': Payment.PAYMENT_RECEIVED}, format='json')

        payment = Payment.objects.get(pk=payment_id)
        earning = Earnings.objects.get(payment=payment)
        self.assertEqual(skipped.status_code, 400)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(processing.status_code, 200)
        self.assertEqual(received.status_code, 200)
        self.assertEqual(payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(payment.amount, self.bid.amount)
        self.assertIsNone(payment.provider_transaction_reference)
        self.assertEqual(earning.freelancer, self.freelancer)
        self.assertEqual(earning.job, self.job)
        self.assertEqual(earning.amount, self.bid.amount)
        self.assertEqual(Earnings.objects.filter(payment=payment).count(), 1)

    def test_clients_and_freelancers_only_see_their_payments(self):
        created = self._create_payment()
        payment_id = created.data['id']
        own = self.client_api.get(reverse('payment-detail', args=[payment_id]))
        freelancer = self.freelancer_api.get(reverse('payment-detail', args=[payment_id]))
        hidden = self.other_client_api.get(reverse('payment-detail', args=[payment_id]))
        listed = self.other_freelancer_api.get(reverse('payments'))

        self.assertEqual(own.status_code, 200)
        self.assertEqual(freelancer.status_code, 200)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(listed.data['results'], [])

    def test_existing_bid_and_task_flow_does_not_create_a_payment(self):
        job = Job.objects.create(
            title='Flow check',
            description='Keep the hiring flow',
            budget=Decimal('800.00'),
            deadline=date(2026, 12, 1),
            created_by=self.client_user,
            status='OPEN',
        )
        bid = Bid.objects.create(
            job=job,
            freelancer=self.freelancer,
            amount=Decimal('700.00'),
            proposal='Ready to start',
            status='PENDING',
        )

        with patch('users.views.safe_send_sms', return_value=None):
            accepted = self.client_api.patch(
                reverse('bid-update', args=[bid.id]),
                {'status': 'ACCEPTED'},
                format='json',
            )
        task = Task.objects.get(job=job, freelancer=self.freelancer)
        completed = self.freelancer_api.patch(
            reverse('task-update', args=[task.id]),
            {'status': 'COMPLETED'},
            format='json',
        )

        job.refresh_from_db()
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(job.status, 'COMPLETED')
        self.assertEqual(Payment.objects.filter(job=job).count(), 0)
        self.assertEqual(Earnings.objects.filter(job=job).count(), 0)


class PayoutFoundationTests(PaymentAPIMixin, TestCase):
    def setUp(self):
        super().setUp()
        created = self._create_payment()
        self.payment = Payment.objects.get(pk=created.data['id'])
        self.staff_api.patch(
            reverse('payment-detail', args=[self.payment.id]),
            {'status': Payment.PAYMENT_PROCESSING},
            format='json',
        )
        self.staff_api.patch(
            reverse('payment-detail', args=[self.payment.id]),
            {'status': Payment.PAYMENT_RECEIVED},
            format='json',
        )
        self.payment.refresh_from_db()

    def _payout_payload(self, **extra):
        payload = {
            'payment': self.payment.id,
            'destination_country': 'NG',
            'destination_currency': 'NGN',
            'payout_method': 'MOBILE_MONEY',
            'destination_reference': 'secret-account-999',
        }
        payload.update(extra)
        return payload

    def test_payout_requires_a_received_payment(self):
        pending_job, _bid = self._accepted_job(
            self.client_user,
            self.freelancer,
            Decimal('900.00'),
        )
        pending = Payment.objects.create(
            job=pending_job,
            client=self.client_user,
            freelancer=self.freelancer,
            amount=Decimal('900.00'),
            currency='KES',
        )
        response = self.freelancer_api.post(
            reverse('payouts'),
            self._payout_payload(payment=pending.id),
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Payout.objects.count(), 0)

    def test_payout_uses_payment_amount_and_freelancer(self):
        response = self.freelancer_api.post(
            reverse('payouts'),
            self._payout_payload(
                amount='1.00',
                currency='USD',
                freelancer=self.other_freelancer.id,
                transaction_reference='CLIENT-PAYOUT',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payout = Payout.objects.get(pk=response.data['id'])
        earning = Earnings.objects.get(payment=self.payment)
        self.assertEqual(payout.freelancer, self.freelancer)
        self.assertEqual(payout.amount, self.payment.amount)
        self.assertEqual(payout.currency, self.payment.currency)
        self.assertEqual(payout.status, Payout.PAYOUT_PENDING)
        self.assertEqual(payout.destination_country, 'NG')
        self.assertEqual(payout.destination_currency, 'NGN')
        self.assertIsNone(payout.provider_transaction_reference)
        self.assertRegex(payout.transaction_reference, PAYOUT_REFERENCE)
        self.assertNotEqual(payout.transaction_reference, 'CLIENT-PAYOUT')
        self.assertNotIn('destination_reference', response.data)
        self.assertNotIn('secret-account-999', response.content.decode())
        self.assertEqual(earning.payout, payout)

    def test_first_payout_links_the_existing_earning(self):
        response = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        earning = Earnings.objects.get(payment=self.payment)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(earning.payout_id, response.data['id'])
        self.assertEqual(earning.payout.status, Payout.PAYOUT_PENDING)

    def test_failed_payout_is_replaced_on_the_same_earning(self):
        first = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        payout_a = Payout.objects.get(pk=first.data['id'])
        failed = self.staff_api.patch(
            reverse('payout-detail', args=[payout_a.id]),
            {'status': Payout.PAYOUT_FAILED},
            format='json',
        )
        second = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        payout_a.refresh_from_db()
        payout_b = Payout.objects.get(pk=second.data['id'])
        earning = Earnings.objects.get(payment=self.payment)
        self.payment.refresh_from_db()

        self.assertEqual(failed.status_code, 200)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(earning.payout_id, payout_b.id)
        self.assertEqual(payout_a.status, Payout.PAYOUT_FAILED)
        self.assertEqual(payout_b.status, Payout.PAYOUT_PENDING)
        self.assertNotEqual(payout_a.transaction_reference, payout_b.transaction_reference)
        self.assertEqual(payout_b.amount, self.payment.amount)
        self.assertEqual(payout_b.freelancer_id, self.payment.freelancer_id)
        self.assertEqual(payout_b.currency, self.payment.currency)
        self.assertEqual(self.payment.status, Payment.PAYMENT_RECEIVED)

    def test_cancelled_payout_is_replaced_on_the_same_earning(self):
        first = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        payout_a = Payout.objects.get(pk=first.data['id'])
        cancelled = self.staff_api.patch(
            reverse('payout-detail', args=[payout_a.id]),
            {'status': Payout.PAYOUT_CANCELLED},
            format='json',
        )
        second = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        payout_a.refresh_from_db()
        earning = Earnings.objects.get(payment=self.payment)

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Earnings.objects.filter(payment=self.payment).count(), 1)
        self.assertEqual(earning.payout_id, second.data['id'])
        self.assertEqual(payout_a.status, Payout.PAYOUT_CANCELLED)
        self.assertEqual(earning.payout.status, Payout.PAYOUT_PENDING)

    def test_unrelated_freelancer_cannot_view_or_create_payout(self):
        created = self.freelancer_api.post(reverse('payouts'), self._payout_payload(), format='json')
        payout_id = created.data['id']
        hidden = self.other_freelancer_api.get(reverse('payout-detail', args=[payout_id]))
        forbidden = self.other_freelancer_api.post(
            reverse('payouts'),
            self._payout_payload(),
            format='json',
        )
        visible = self.client_api.get(reverse('payout-detail', args=[payout_id]))

        self.assertEqual(created.status_code, 201)
        self.assertEqual(hidden.status_code, 404)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(visible.status_code, 200)

    def test_payout_reference_is_unique_and_mismatched_freelancer_is_rejected(self):
        first = Payout.objects.create(
            payment=self.payment,
            freelancer=self.freelancer,
            amount=Decimal('1.00'),
            currency='USD',
            destination_country='KE',
            destination_currency='KES',
            payout_method='BANK_TRANSFER',
        )
        self.assertEqual(first.amount, self.payment.amount)
        self.assertEqual(first.currency, 'KES')
        other_job, _bid = self._accepted_job(self.other_client, self.other_freelancer, Decimal('80.00'))
        other_payment = Payment.objects.create(
            job=other_job,
            client=self.other_client,
            freelancer=self.other_freelancer,
            amount=Decimal('80.00'),
            currency='KES',
        )
        second = Payout.objects.create(
            payment=other_payment,
            freelancer=other_payment.freelancer,
            amount=other_payment.amount,
            currency='KES',
            destination_country='KE',
            destination_currency='KES',
            payout_method='BANK_TRANSFER',
        )
        second.transaction_reference = first.transaction_reference
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                second.save()

        mismatched = Payout(
            payment=self.payment,
            freelancer=self.other_freelancer,
            amount=self.payment.amount,
            currency='KES',
            destination_country='KE',
            destination_currency='KES',
            payout_method='MOBILE_MONEY',
        )
        with self.assertRaises(ValidationError):
            mismatched.save()

    def test_payout_starts_pending_and_rejects_invalid_transitions(self):
        created = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        duplicate = self.client_api.post(reverse('payouts'), self._payout_payload(), format='json')
        detail = reverse('payout-detail', args=[created.data['id']])
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(created.data['status'], Payout.PAYOUT_PENDING)
        self.assertIsNone(created.data['provider_transaction_reference'])

        skipped = self.staff_api.patch(detail, {'status': Payout.PAYOUT_PAID}, format='json')
        forbidden = self.freelancer_api.patch(detail, {'status': Payout.PAYOUT_PROCESSING}, format='json')
        processing = self.staff_api.patch(
            detail,
            {'status': Payout.PAYOUT_PROCESSING, 'provider_transaction_reference': 'fake-payaza-payout'},
            format='json',
        )

        payout = Payout.objects.get(pk=created.data['id'])
        self.assertEqual(skipped.status_code, 400)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(processing.status_code, 200)
        self.assertEqual(payout.status, Payout.PAYOUT_PROCESSING)
        self.assertIsNone(payout.provider_transaction_reference)

    def test_negative_payout_amount_is_rejected_without_a_payment_amount(self):
        payout = Payout(
            freelancer=self.freelancer,
            amount=Decimal('-1.00'),
            currency='KES',
            destination_country='KE',
            destination_currency='KES',
            payout_method='MOBILE_MONEY',
        )
        with self.assertRaises(ValidationError):
            payout.save()


@override_settings(
    PAYAZA_PUBLIC_KEY='pk_live_should_not_appear',
    PAYAZA_SECRET_KEY='sk_live_should_not_appear',
)
class PaymentResponseSecurityTests(PaymentAPIMixin, TestCase):
    def test_responses_do_not_expose_payaza_credentials(self):
        created = self._create_payment()
        self.staff_api.patch(
            reverse('payment-detail', args=[created.data['id']]),
            {'status': Payment.PAYMENT_PROCESSING},
            format='json',
        )
        received = self.staff_api.patch(
            reverse('payment-detail', args=[created.data['id']]),
            {'status': Payment.PAYMENT_RECEIVED},
            format='json',
        )
        payout = self.freelancer_api.post(
            reverse('payouts'),
            {
                'payment': created.data['id'],
                'destination_country': 'KE',
                'destination_currency': 'KES',
                'payout_method': 'BANK_TRANSFER',
            },
            format='json',
        )
        earnings = self.freelancer_api.get(reverse('earnings'))
        bodies = [
            created.content.decode(),
            received.content.decode(),
            payout.content.decode(),
            earnings.content.decode(),
        ]
        secret_values = [
            settings.PAYAZA_PUBLIC_KEY,
            settings.PAYAZA_SECRET_KEY,
            'Authorization',
            'Payaza ',
        ]
        for body in bodies:
            for secret in secret_values:
                self.assertNotIn(secret, body)
        self.assertEqual(payout.status_code, 201)
