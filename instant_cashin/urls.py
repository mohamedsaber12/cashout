from django.urls import path

from .views import (DownloadPendingOrangeInstantTransactionsView,
                    BankTransactionsListView,
                    InstantTransactionsListView,
                    PendingOrangeInstantTransactionsListView,
                    ServeDownloadingInstantTransactionsView)


app_name = 'instant_cashin'

urlpatterns = [
    path('instant-transactions/wallets/', InstantTransactionsListView.as_view(), name='wallets_trx_list'),
    path('instant-transactions/banks/', BankTransactionsListView.as_view(), name='banks_trx_list'),
    path('instant-transactions/pending/', PendingOrangeInstantTransactionsListView.as_view(), name='pending_list'),
    path('instant-transactions/download/', DownloadPendingOrangeInstantTransactionsView.as_view(), name='download'),
    path('instant-transactions/serve/', ServeDownloadingInstantTransactionsView.as_view(), name='serve_download')
]
