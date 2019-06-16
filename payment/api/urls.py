from django.urls import path
from .views import TransactionCallbackAPIView

app_name = 'payment_api'
urlpatterns = [
    path('trx/', TransactionCallbackAPIView.as_view())
]
