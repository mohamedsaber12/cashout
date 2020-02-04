from django.urls import path

from data import views

app_name = 'data'

urlpatterns = [
    path('', views.redirect_home, name='main_view'),
    path('collection/', views.collection_home, name='collection_home'),
    path('disbursement/', views.disbursement_home, name='disbursement_home'),
    path('delete/(<pk>/', views.FileDeleteView.as_view(), name='file_delete'),
    path('documents/<doc_id>/', views.document_view, name='doc_viewer'),
    path('download_doc/<doc_id>/', views.doc_download, name='download_doc'),
    path('format/list',views.FormatListView.as_view(),name='list_format'),
    path('document/collection/<pk>/', views.RetrieveCollectionData.as_view(), name='doc_collection_detail'),
]
