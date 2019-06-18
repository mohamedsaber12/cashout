from django.urls import path
from users.views import ExpiringAuthToken

from .views import BillInquiryAPIView
app_name = 'data_api'
urlpatterns = [
    path('token-auth/', ExpiringAuthToken.as_view()),
    path('bill/<super>/', BillInquiryAPIView.as_view())
]
