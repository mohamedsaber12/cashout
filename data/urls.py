from django.urls import path

from data import views

app_name = 'data'

urlpatterns = [
    path('', views.redirect_home, name='main_view'),
    path('disbursement/e-wallets/', views.DisbursementHomeView.as_view(), name='e_wallets_home'),
    path('disbursement/bank-wallets/', views.BanksHomeView.as_view(), name='bank_wallets_home'),
    path('disbursement/bank-cards/', views.BanksHomeView.as_view(), name='bank_cards_home'),
    path('delete/(<pk>/', views.FileDeleteView.as_view(), name='file_delete'),
    path('documents/<doc_id>/', views.document_view, name='doc_viewer'),
    path('download_doc/<doc_id>/', views.doc_download, name='download_doc'),
    path('format/list',views.FormatListView.as_view(),name='list_format'),
]
