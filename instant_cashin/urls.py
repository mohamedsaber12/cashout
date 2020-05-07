from django.urls import path

from .views import (DownloadPendingOrangeInstantTransactionsView,
                    InstantTransactionsListView,
                    PendingOrangeInstantTransactionsListView,
                    ServeDownloadingInstantTransactionsView)


app_name = 'instant_cashin'

urlpatterns = [
    path('instant-transactions/', InstantTransactionsListView.as_view(), name='transactions_list'),
    path('instant-transactions/pending/', PendingOrangeInstantTransactionsListView.as_view(), name='pending_list'),
    path('instant-transactions/download/', DownloadPendingOrangeInstantTransactionsView.as_view(), name='download'),
    path('instant-transactions/serve/', ServeDownloadingInstantTransactionsView.as_view(), name='serve_download')
]
