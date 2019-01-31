from django.urls import path
from rest_framework_expiring_authtoken import views

from .views import BillInquiryAPIView
app_name = 'data_api'
urlpatterns = [
    path('token-auth/', views.obtain_expiring_auth_token),
    path('bill/<super>/', BillInquiryAPIView.as_view())
]
