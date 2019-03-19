from django.urls import path

from disb.views import (disburse, disbursement_list,
                        failed_disbursed_for_download, SuperAdminAgentsSetup, BalanceInquiry)

app_name = 'disbursement'

urlpatterns = [
    path('disburse_call/<doc_id>/', disburse, name='disburse'),  # path for app view
    path('disburse/report/<doc_id>/', disbursement_list, name='disbursed_data'),
    path('disburse/export_failed_download/<doc_id>/',
         failed_disbursed_for_download, name='download_failed'),
    path('client/creation/agents/<token>/', SuperAdminAgentsSetup.as_view(), name='add_agents'),
    path('agent/balance-inquiry',
         BalanceInquiry.as_view(), name='balance_inquiry'),
    
]
