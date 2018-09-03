from django.urls import path

from disb.views import disburse, disbursement_list, generate_failed_disbursement_data, \
    failed_disbursed_for_download

app_name = 'disbursement'

urlpatterns = [
    path('disburse_call/<doc_id>/', disburse, name='disburse'),  # path for app view
    path('disburse/report/<doc_id>/', disbursement_list, name='disbursed_data'),
    path('disburse/export_failed/<doc_id>/', generate_failed_disbursement_data, name='export_failed'),
    path('disburse/export_failed_download/', failed_disbursed_for_download, name='download_failed'),
]

