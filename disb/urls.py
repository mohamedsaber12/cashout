from django.urls import path

from .views import (BalanceInquiry, SuperAdminAgentsSetup, disburse,
                    disbursement_list, download_failed_validation_file,
                    failed_disbursed_for_download)


app_name = 'disbursement'


client_urls = [
    path('agent/balance-inquiry', BalanceInquiry.as_view(), name='balance_inquiry'),
    path('client/creation/agents/<token>/', SuperAdminAgentsSetup.as_view(), name='add_agents'),
]

urlpatterns = [
    path('disburse_call/<doc_id>/', disburse, name='disburse'),
    path('disburse/report/<doc_id>/', disbursement_list, name='disbursed_data'),
    path('disburse/export_failed_download/<doc_id>/', failed_disbursed_for_download, name='download_failed'),
    path('disburse/export_failed_validation_download/<doc_id>/',
         download_failed_validation_file, name='download_validation_failed'),
]

urlpatterns += client_urls
