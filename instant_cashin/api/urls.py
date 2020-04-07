from django.urls import path

from .base_views import BudgetInquiryAPIView, InstantDisbursementAPIView


app_name = 'instant_api'

urlpatterns = [
    # User Inquiry Feature is DISABLED for now! and HIDDEN from the Docs.
    # path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),

    path('budget-inquiry/', BudgetInquiryAPIView.as_view(), name='budget_inquiry'),
    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
]
