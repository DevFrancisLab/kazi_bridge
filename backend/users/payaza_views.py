"""Development-only Payaza connectivity check."""

from django.conf import settings
from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .payaza import fetch_main_account_enquiry, fetch_main_accounts, fetch_main_accounts_requests


class PayazaTestConnectionView(APIView):
    """Call Payaza's main-accounts endpoint and return a sanitized result.

    Available only while Django DEBUG is on. This is not a payment endpoint.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.DEBUG:
            raise Http404("Payaza connectivity test is only available in development.")

        result = fetch_main_accounts()
        if result.get("error") == "missing_configuration":
            status_code = 503
        elif result.get("error") == "timeout":
            status_code = 504
        elif result.get("success"):
            status_code = 200
        else:
            status_code = 502
        return Response(result, status=status_code)


class PayazaTestConnectionRequestsView(APIView):
    """Same Payaza main-accounts check, using the requests library.

    Available only while Django DEBUG is on. This is not a payment endpoint.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.DEBUG:
            raise Http404("Payaza connectivity test is only available in development.")

        result = fetch_main_accounts_requests()
        if result.get("error") == "missing_configuration":
            status_code = 503
        elif result.get("error") == "timeout":
            status_code = 504
        elif result.get("success"):
            status_code = 200
        else:
            status_code = 502
        return Response(result, status=status_code)


class PayazaTestAccountEnquiryView(APIView):
    """Call the Payaza account-enquiry path confirmed by Payaza support.

    Available only while Django DEBUG is on. This is not a payment endpoint.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.DEBUG:
            raise Http404("Payaza account enquiry is only available in development.")

        result = fetch_main_account_enquiry()
        if result.get("error") == "missing_configuration":
            status_code = 503
        elif result.get("error") == "timeout":
            status_code = 504
        elif result.get("success"):
            status_code = 200
        else:
            status_code = 502
        return Response(result, status=status_code)
