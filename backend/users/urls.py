from django.urls import path
from .views import RegisterView, LoginView, LogoutView, MeView, ProfileUpdateView, JobListCreateView, TaskListView, EarningsListView, TaskUpdateView
from .views import BidListCreateView, JobBidsListView, BidUpdateView, MessageListCreateView, JobMessagesListView, FreelancersListView, SendSMSView
from .payaza_views import (
    PayazaTestAccountEnquiryView,
    PayazaTestConnectionRequestsView,
    PayazaTestConnectionView,
)
from .payment_views import (
    PaymentDetailView,
    PaymentListCreateView,
    PaymentPayazaCollectionView,
    PaymentPayazaStatusView,
    PaymentPayazaWebhookView,
    PayoutDetailView,
    PayoutListCreateView,
    PayoutPayazaTransferView,
    PayoutPayazaStatusView,
    PayoutPayazaWebhookView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('profile/', ProfileUpdateView.as_view(), name='profile-update'),
    path('jobs/', JobListCreateView.as_view(), name='jobs'),
    path('bids/', BidListCreateView.as_view(), name='bids'),
    path('jobs/<int:job_id>/bids/', JobBidsListView.as_view(), name='job-bids'),
    path('bids/<int:pk>/', BidUpdateView.as_view(), name='bid-update'),
    path('tasks/<int:pk>/', TaskUpdateView.as_view(), name='task-update'),
    path('tasks/', TaskListView.as_view(), name='tasks'),
    path('earnings/', EarningsListView.as_view(), name='earnings'),
    path('payments/', PaymentListCreateView.as_view(), name='payments'),
    path(
        'payments/payaza/webhook/',
        PaymentPayazaWebhookView.as_view(),
        name='payment-payaza-webhook',
    ),
    path(
        'payments/payaza/payout-webhook/',
        PayoutPayazaWebhookView.as_view(),
        name='payout-payaza-webhook',
    ),
    path('payments/<int:pk>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/<int:pk>/payaza/', PaymentPayazaCollectionView.as_view(), name='payment-payaza'),
    path(
        'payments/<int:pk>/payaza/status/',
        PaymentPayazaStatusView.as_view(),
        name='payment-payaza-status',
    ),
    path('payouts/', PayoutListCreateView.as_view(), name='payouts'),
    path('payouts/<int:pk>/', PayoutDetailView.as_view(), name='payout-detail'),
    path('payouts/<int:pk>/payaza/', PayoutPayazaTransferView.as_view(), name='payout-payaza'),
    path(
        'payouts/<int:pk>/payaza/status/',
        PayoutPayazaStatusView.as_view(),
        name='payout-payaza-status',
    ),
    path('messages/', MessageListCreateView.as_view(), name='messages'),
    path('jobs/<int:job_id>/messages/', JobMessagesListView.as_view(), name='job-messages'),
    path('freelancers/', FreelancersListView.as_view(), name='freelancers'),
    path('sms/', SendSMSView.as_view(), name='send-sms'),
    path('payaza/test-connection/', PayazaTestConnectionView.as_view(), name='payaza-test-connection'),
    path(
        'payaza/test-connection-requests/',
        PayazaTestConnectionRequestsView.as_view(),
        name='payaza-test-connection-requests',
    ),
    path(
        'payaza/test-account-enquiry/',
        PayazaTestAccountEnquiryView.as_view(),
        name='payaza-test-account-enquiry',
    ),
]

