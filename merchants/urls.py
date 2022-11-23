from django.urls import path

from merchants import views

app_name = 'merchant'

urlpatterns = [
    path('download_file/<file_id>/', views.DownloadFile.as_view(), name='download_file'),

]
    