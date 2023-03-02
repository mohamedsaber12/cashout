from django.urls import path

from .views import (BudgetUpdateView, IncreaseBalanceRequestView,
                    ListIncreaseBalanceRequestView, MerchantLimitUpdateView)

app_name = "utilities"

urlpatterns = [
    path(
        'budget/edit/<str:username>/', BudgetUpdateView.as_view(), name='budget_update'
    ),
    path(
        'budget/transfer-request/',
        IncreaseBalanceRequestView.as_view(),
        name='transfer_request',
    ),
    path(
        'budget/list-transfer-request/',
        ListIncreaseBalanceRequestView.as_view(),
        name='list_transfer_request',
    ),
    path(
        'merchant/limit/<username>/edit/',
        MerchantLimitUpdateView.as_view(),
        name='merchant_limit_edit',
    ),
]
