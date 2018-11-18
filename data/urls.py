from django.urls import path

from data import views

app_name = 'data'

urlpatterns = [
    path('download_temp/', views.download_excel_with_trx_temp_view,
         name='download_xls_temp'),
    path('', views.file_upload, name='main_view'),
    path('edit/<pk>/', views.file_update, name='file_edit'),
    path('delete/(<pk>/', views.file_delete, name='file_delete'),
    path('documents/<doc_id>/', views.document_view, name='doc_viewer'),
    path('download_doc/<doc_id>/', views.doc_download, name='download_doc'),
    path('doc_details_list/', views.DocumentDetailsListView.as_view(),
         name='doc_details_list'),
]
