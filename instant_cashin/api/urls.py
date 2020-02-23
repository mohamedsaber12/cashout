from django.urls import path

from .views import InstantDisbursementAPIView


app_name = 'instant_api'


urlpatterns = [
    # User Inquiry Feature is DISABLED for now! and HIDDEN from the Docs.
    # path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),

    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
]
