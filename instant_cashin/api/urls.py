from django.urls import path

from .views import InstantUserInquiryAPIView, InstantDisbursementAPIView


app_name = 'instant_api'


urlpatterns = [
    path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),
    path('disburse/', InstantDisbursementAPIView.as_view(), name='instant_disburse'),
]
