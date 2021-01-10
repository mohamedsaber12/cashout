from django.urls import path

from .views import BudgetUpdateView, IncreaseBalanceRequestView

app_name = "utilities"

urlpatterns = [
    path('budget/edit/<str:username>/', BudgetUpdateView.as_view(), name='budget_update'),
    path('budget/transfer-request/', IncreaseBalanceRequestView.as_view(), name='transfer_request'),
]
