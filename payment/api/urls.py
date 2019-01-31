from django.urls import path
from rest_framework_expiring_authtoken import views

from .views import TransactionCallbackAPIView

app_name = 'payment_api'
urlpatterns = [
    path('token-auth/', views.obtain_expiring_auth_token),
    path('trx/', TransactionCallbackAPIView.as_view())
]
