from django.urls import path

from .views import BudgetUpdateView, IncreaseBalanceRequestView

app_name = "utilities"

urlpatterns = [
    path('agent/budget/edit/<str:username>/', BudgetUpdateView.as_view(), name='budget_update'),
    path('agent/budget/increase_balance', IncreaseBalanceRequestView.as_view(), name='increase_balance'),
]
