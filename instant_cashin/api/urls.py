from django.urls import path

from .base_views import (
    AmanTransactionCallbackHandlerAPIView, BudgetInquiryAPIView,
    BulkTransactionInquiryAPIView, InstantDisbursementAPIView,
    SingleStepDisbursementAPIView
)


app_name = 'instant_api'

urlpatterns = [
    # User Inquiry Feature is DISABLED for now! and HIDDEN from the Docs.
    # path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),

    path('budget/inquire/', BudgetInquiryAPIView.as_view(), name='budget_inquiry'),
    path('transaction/aman-callback/', AmanTransactionCallbackHandlerAPIView.as_view(), name='aman_trx_callback'),
    path('transaction/inquire/', BulkTransactionInquiryAPIView.as_view(), name='bulk_transaction_inquiry'),
    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
    path('disburse/single-step/', SingleStepDisbursementAPIView.as_view(), name='disburse_single_step'),
    
]
