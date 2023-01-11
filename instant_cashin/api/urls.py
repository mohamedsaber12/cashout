from django.urls import path

from .base_views import (  # TopupbalanceAPIView,
    AmanTransactionCallbackHandlerAPIView, BudgetInquiryAPIView,
    BulkTransactionInquiryAPIView, Calculate_fees_and_vat_APIView,
    CancelAmanTransactionAPIView, HoldBalanceAPIView,
    InstantDisbursementAPIView, ReleaseBalanceAPIView,
    SingleStepDisbursementAPIView)

app_name = 'instant_api'

urlpatterns = [
    # User Inquiry Feature is DISABLED for now! and HIDDEN from the Docs.
    # path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),
    path('budget/inquire/', BudgetInquiryAPIView.as_view(), name='budget_inquiry'),
    path(
        'transaction/aman-callback/',
        AmanTransactionCallbackHandlerAPIView.as_view(),
        name='aman_trx_callback',
    ),
    path(
        'transaction/inquire/',
        BulkTransactionInquiryAPIView.as_view(),
        name='bulk_transaction_inquiry',
    ),
    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
    path('hold-balance/', HoldBalanceAPIView.as_view(), name='hold_balance'),
    path('release-balance/', ReleaseBalanceAPIView.as_view(), name='release_balance'),
    path(
        'disburse/single-step/',
        SingleStepDisbursementAPIView.as_view(),
        name='disburse_single_step',
    ),
    path(
        'transaction/aman/cancel/',
        CancelAmanTransactionAPIView.as_view(),
        name='cancel_aman_transaction',
    ),
    # path('topupbalance-request/',TopupbalanceAPIView.as_view(),name='topupbalance_request'),
    path(
        'calc-fees-vat/', Calculate_fees_and_vat_APIView.as_view(), name='calc_fees_vat'
    ),
]
