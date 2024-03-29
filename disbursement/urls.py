from django.urls import path

from .views import (
    AgentsListView, BalanceInquiry,
    SuperAdminAgentsSetup, disburse, DisbursementDocTransactionsView,
    download_failed_validation_file, ExportClientsTransactionsReportPerSuperAdmin,
    failed_disbursed_for_download, SingleStepTransactionsView,
    DownloadSampleSheetView, download_exported_transactions, HomeView,
    DisbursementDataListView, OrangeBankWalletListView, BanksListView
)


app_name = 'disbursement'

client_urls = [
    path('agents/', AgentsListView.as_view(), name='agents_list'),
    path('home/', HomeView.as_view(), name='home_root'),
    path('home/portal-transactions/', DisbursementDataListView.as_view(), name='vf_et_aman_list'),
    path('home/portal-transactions-orange/', OrangeBankWalletListView.as_view(), name='orange_bank_wallet_list'),
    path('home/portal-transactions-banks/', BanksListView.as_view(), name='banks_list'),
    path('budget/inquiry/<str:username>/', BalanceInquiry.as_view(), name='balance_inquiry'),
    path('client/creation/agents/<token>/', SuperAdminAgentsSetup.as_view(), name='add_agents'),
]

urlpatterns = [
    path('disburse/single-step/', SingleStepTransactionsView.as_view(), name='single_step_list_create'),
    path('disburse_call/<doc_id>/', disburse, name='disburse'),
    path('disburse/export-sample-file/', DownloadSampleSheetView.as_view(), name='export_sample_file'),
    path('disburse/report/<doc_id>/', DisbursementDocTransactionsView.as_view(), name='disbursed_data'),
    path('disburse/export_failed_download/<doc_id>/', failed_disbursed_for_download, name='download_failed'),
    path('disburse/download_exported_transactions/', download_exported_transactions, name='download_exported'),
    path(
            'disburse/export-clients-transactions-report/',
            ExportClientsTransactionsReportPerSuperAdmin.as_view(),
            name='export_clients_transactions_report'
    ),
    path('disburse/export_failed_validation_download/<doc_id>/',
         download_failed_validation_file, name='download_validation_failed'),
]

urlpatterns += client_urls
