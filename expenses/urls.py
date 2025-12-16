from django.urls import path
from .views import (
    dashboard,
    transactions_list,
    add_transaction,
    edit_transaction,
    delete_transaction
)

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('transactions/', transactions_list, name='transactions'),
    path('add/', add_transaction, name='add_transaction'),
    path('edit/<int:pk>/', edit_transaction, name='edit_transaction'),
    path('delete/<int:pk>/', delete_transaction, name='delete_transaction'),
]
