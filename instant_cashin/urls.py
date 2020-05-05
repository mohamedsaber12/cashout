from django.urls import path

from .views import PendingOrangeInstantTransactionsListView


app_name = 'instant_cashin'

urlpatterns = [
    path('instant-transactions/pending/', PendingOrangeInstantTransactionsListView.as_view(), name='home'),
]
