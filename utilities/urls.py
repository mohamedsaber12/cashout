from django.urls import path

from .views import BudgetUpdateView

app_name = "utilities"

urlpatterns = [
    path('agent/budget/edit/<str:username>/', BudgetUpdateView.as_view(), name='budget_update'),
]
