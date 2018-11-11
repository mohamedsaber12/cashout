from django.urls import path

from disb.api.views import (AllowDocDisburse, DisburseAPIView,
                            DisburseCallBack, RetrieveDocData)

app_name = 'disb_api'

urlpatterns = [
    path('disburse/apmORlUSt8qNdF54/',
         DisburseAPIView.as_view(), name='disburse'),
    path('disburse/callback/', DisburseCallBack.as_view(),
         name='disburse_callback'),
    path('disburse/allow/<doc_id>/',
         AllowDocDisburse.as_view(), name='allow_doc_disburse'),
    path('doc/<doc_id>/', RetrieveDocData.as_view(), name='docrows'),

]
