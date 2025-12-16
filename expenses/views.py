from decimal import Decimal
from datetime import date, datetime, timedelta
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib import messages

from .models import Transaction, Category
from .forms import TransactionForm


# ---------------- DASHBOARD VIEW (NO TABLE) ----------------
def dashboard(request):
    # ----- Get filter values from URL -----
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category')
    tx_type = request.GET.get('type')

    # ----- Convert string to date safely -----
    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    s_date = parse_date(start_date)
    e_date = parse_date(end_date)

    # ----- Base queryset -----
    transactions = Transaction.objects.all()

    # ----- Apply filters -----
    if s_date:
        transactions = transactions.filter(date__gte=s_date)

    if e_date:
        transactions = transactions.filter(date__lte=e_date)

    if category_id and category_id.isdigit():
        transactions = transactions.filter(category__id=int(category_id))

    if tx_type in ('income', 'expense'):
        transactions = transactions.filter(type=tx_type)

    # ----- Calculate totals -----
    total_income = transactions.filter(type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    total_expense = transactions.filter(type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    balance = total_income - total_expense

    # ----- Categories for dropdown -----
    categories = Category.objects.all().order_by('name')

    # ----- Pie Chart: Expense by Category -----
    category_data = transactions.filter(type='expense') \
        .values('category__name') \
        .annotate(total=Sum('amount'))

    expense_cat_labels = [
        item['category__name'] or 'Uncategorized'
        for item in category_data
    ]

    expense_cat_values = [
        float(item['total']) for item in category_data
    ]

    # ----- Bar Chart: Last 7 Days Expense -----
    end_day = e_date if e_date else date.today()
    start_day = end_day - timedelta(days=6)

    last7_labels = []
    last7_values = []

    for i in range(7):
        current_day = start_day + timedelta(days=i)
        last7_labels.append(current_day.strftime('%Y-%m-%d'))

        daily_total = transactions.filter(
            type='expense',
            date=current_day
        ).aggregate(total=Sum('amount'))['total']

        last7_values.append(float(daily_total) if daily_total else 0)

    # ----- Send data to template -----
    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'categories': categories,

        'expense_cat_labels_json': json.dumps(expense_cat_labels),
        'expense_cat_values_json': json.dumps(expense_cat_values),
        'last7_labels_json': json.dumps(last7_labels),
        'last7_values_json': json.dumps(last7_values),

        'filter_start_date': start_date or '',
        'filter_end_date': end_date or '',
        'filter_category': category_id or '',
        'filter_type': tx_type or '',
    }

    return render(request, 'expenses/dashboard.html', context)


# ---------------- TRANSACTIONS LIST VIEW ----------------
def transactions_list(request):
    transactions = Transaction.objects.order_by('-date')[:5]

    return render(
        request,
        'expenses/transaction_list.html',
        {'transactions': transactions}
    )


# ---------------- ADD TRANSACTION ----------------
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction added successfully')
            return redirect('transactions')
    else:
        form = TransactionForm()

    return render(request, 'expenses/add_transaction.html', {'form': form})


# ---------------- EDIT TRANSACTION ----------------
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully')
            return redirect('transactions')
    else:
        form = TransactionForm(instance=transaction)

    return render(
        request,
        'expenses/edit_transaction.html',
        {'form': form, 'transaction': transaction}
    )


# ---------------- DELETE TRANSACTION ----------------
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully')
        return redirect('transactions')

    return render(
        request,
        'expenses/delete_transaction.html',
        {'transaction': transaction}
    )
