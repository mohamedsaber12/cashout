from django.urls import path

from .views import BankTransactionsListView, InstantTransactionsListView


app_name = 'instant_cashin'

urlpatterns = [
    path('instant-transactions/wallets/', InstantTransactionsListView.as_view(), name='wallets_trx_list'),
    path('instant-transactions/banks/', BankTransactionsListView.as_view(), name='banks_trx_list'),
]
