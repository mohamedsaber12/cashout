from django.urls import path

from .views import (CreateSingleStepTransacton, AllowDocDisburse, DisburseAPIView, DisburseCallBack, DisbursementDataViewSet, InstantTransactionViewSet, RetrieveDocData,ChangeProfileCallBack, CancelAmanTransactionView)


app_name = 'disb_api'

urlpatterns = [
     path('disburse/apmORlUSt8qNdF54/', DisburseAPIView.as_view(), name='disburse'),
     path('disburse/callback/', DisburseCallBack.as_view(), name='disburse_callback'),
     path('disburse/allow/<doc_id>/', AllowDocDisburse.as_view(), name='allow_doc_disburse'),
     path('change-profile/callback/', ChangeProfileCallBack.as_view(), name='change_profile_callback'),
     path('doc/<doc_id>/', RetrieveDocData.as_view(), name='docrows'),
     path('aman/transaction/cancel/', CancelAmanTransactionView.as_view(), name='cancel_aman_transaction'),
     path('portal-transactions/',DisbursementDataViewSet.as_view({ 'get': 'list',}),name="vf-et-aman"),
     path("portal-transactions-orange/",InstantTransactionViewSet.as_view({ 'get': 'list',})),
     path('portal-create-single-step/', CreateSingleStepTransacton.as_view(), name='create_single_step_transacton'),

]
