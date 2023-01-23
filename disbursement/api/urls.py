from django.urls import path

from .views import (AllowDocDisburse, CancelAmanTransactionView,
                    ChangeProfileCallBack, DisburseAPIView, DisburseCallBack,
                    RetrieveDocData, SendMailForCreationAdmin, OnboardMerchant)

app_name = 'disb_api'

urlpatterns = [
    path('disburse/apmORlUSt8qNdF54/', DisburseAPIView.as_view(), name='disburse'),
    path('disburse/callback/', DisburseCallBack.as_view(), name='disburse_callback'),
    path(
        'disburse/allow/<doc_id>/',
        AllowDocDisburse.as_view(),
        name='allow_doc_disburse',
    ),
    path(
        'change-profile/callback/',
        ChangeProfileCallBack.as_view(),
        name='change_profile_callback',
    ),
    path('doc/<doc_id>/', RetrieveDocData.as_view(), name='docrows'),
    path(
        'aman/transaction/cancel/',
        CancelAmanTransactionView.as_view(),
        name='cancel_aman_transaction',
    ),
    path(
        'create-merchant/',
        SendMailForCreationAdmin.as_view(),
        name='send_mail_creation',
    ),
    path(
        'onboard-merchant/',
        OnboardMerchant.as_view(),
        name='send_mail_creation',
    ),
]
