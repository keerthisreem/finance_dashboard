from decimal import Decimal
from datetime import date, datetime, timedelta
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib import messages

from .models import Transaction, Category
from .forms import TransactionForm


def home(request):
    """
    Dashboard with optional GET filters:
      - start_date (YYYY-MM-DD)
      - end_date (YYYY-MM-DD)
      - category (category id)
      - type (income / expense / all)
    """
    # --- read filter params from GET ---
    start_date = request.GET.get('start_date')  # e.g. "2025-12-01"
    end_date = request.GET.get('end_date')      # e.g. "2025-12-09"
    category_id = request.GET.get('category')   # category id string
    tx_type = request.GET.get('type')           # 'income' or 'expense' or None

    # parse date strings into date objects (safe)
    def parse_date(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None

    s_date = parse_date(start_date)
    e_date = parse_date(end_date)

    # base queryset (apply filters)
    qs = Transaction.objects.all().order_by('-date')

    if s_date:
        qs = qs.filter(date__gte=s_date)
    if e_date:
        qs = qs.filter(date__lte=e_date)
    if category_id:
        try:
            qs = qs.filter(category__id=int(category_id))
        except ValueError:
            pass
    if tx_type in ('income', 'expense'):
        qs = qs.filter(type=tx_type)

    # totals (based on filtered queryset)
    income_agg = qs.filter(type='income').aggregate(total=Sum('amount'))['total']
    expense_agg = qs.filter(type='expense').aggregate(total=Sum('amount'))['total']
    total_income = income_agg if income_agg is not None else Decimal('0.00')
    total_expense = expense_agg if expense_agg is not None else Decimal('0.00')
    balance = total_income - total_expense

    # Categories list for the filter dropdown
    categories = Category.objects.all().order_by('name')

    # --- Chart A: Expense by Category (pie) based on filtered qs (only expense rows) ---
    cat_qs = qs.filter(type='expense').values('category__id', 'category__name').annotate(total=Sum('amount'))
    expense_cat_labels = [item['category__name'] if item['category__name'] else 'Uncategorized' for item in cat_qs]
    expense_cat_values = [float(item['total']) for item in cat_qs]

    # --- Chart B: Last 7 days expenses (bar) ---
    # Determine end date for last7: if e_date provided use that; else today
    end_for_last7 = e_date if e_date is not None else date.today()
    start_for_last7 = end_for_last7 - timedelta(days=6)
    last7_dates = [start_for_last7 + timedelta(days=i) for i in range(7)]
    last7_labels = [d.strftime("%Y-%m-%d") for d in last7_dates]
    last7_sums = []
    for d in last7_dates:
        s = qs.filter(type='expense', date=d).aggregate(total=Sum('amount'))['total']
        last7_sums.append(float(s) if s is not None else 0.0)

    context = {
        'transactions': qs,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'categories': categories,

        # chart JSON for template
        'expense_cat_labels_json': json.dumps(expense_cat_labels),
        'expense_cat_values_json': json.dumps(expense_cat_values),
        'last7_labels_json': json.dumps(last7_labels),
        'last7_values_json': json.dumps(last7_sums),

        # keep filter values so template can re-populate the form
        'filter_start_date': start_date or '',
        'filter_end_date': end_date or '',
        'filter_category': int(category_id) if category_id and category_id.isdigit() else '',
        'filter_type': tx_type or '',
    }
    return render(request, 'expenses/transaction_list.html', context)


def add_transaction(request):
    """Show add form and save new transaction."""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction added successfully.')
            return redirect('home')
    else:
        form = TransactionForm()
    return render(request, 'expenses/add_transaction.html', {'form': form})


def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully.')
            return redirect('home')
    else:
        form = TransactionForm(instance=transaction)
    return render(request, 'expenses/edit_transaction.html', {'form': form, 'transaction': transaction})


def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully.')
        return redirect('home')
    return render(request, 'expenses/delete_transaction.html', {'transaction': transaction})
