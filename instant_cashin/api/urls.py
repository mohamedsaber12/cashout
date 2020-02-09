from django.urls import path

from .views import InstantUserInquiryAPIView


app_name = 'instant_api'


urlpatterns = [
    path('inquire-user/', InstantUserInquiryAPIView.as_view(), name='inquire_user'),
]
