from django.urls import path

from .views import (DownloadPendingOrangeInstantTransactionsView,
                    PendingOrangeInstantTransactionsListView)

app_name = 'instant_cashin'

urlpatterns = [
    path('instant-transactions/pending/', PendingOrangeInstantTransactionsListView.as_view(), name='home'),
    path('instant-transactions/download/', DownloadPendingOrangeInstantTransactionsView.as_view(), name='download'),
]
