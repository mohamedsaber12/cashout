from django.urls import path

from .views import BudgetInquiryAPIView, InstantDisbursementAPIView


app_name = 'instant_api'


urlpatterns = [
    # User Inquiry Feature is DISABLED for now! and HIDDEN from the Docs.
    # path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),

    path('budget-inquiry/', BudgetInquiryAPIView.as_view(), name='custom_budget_inquiry'),
    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
]
