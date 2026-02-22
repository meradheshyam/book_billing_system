# core/views_purchase.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .models import Invoice, InvoiceItem, Party, Book
from .forms import PurchaseInvoiceForm, PurchaseItemFormSet

@login_required
def purchase_list(request):
    """
    Display list of purchase invoices.
    """
    # Get filter parameters
    status = request.GET.get('status', '')
    supplier = request.GET.get('supplier', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    purchases = Invoice.objects.filter(invoice_type='PURCHASE')
    
    # Apply filters
    if status:
        purchases = purchases.filter(status=status)
    
    if supplier:
        purchases = purchases.filter(party_id=supplier)
    
    if date_from:
        purchases = purchases.filter(invoice_date__gte=date_from)
    
    if date_to:
        purchases = purchases.filter(invoice_date__lte=date_to)
    
    # Search
    search_query = request.GET.get('q', '')
    if search_query:
        purchases = purchases.filter(
            Q(invoice_number__icontains=search_query) |
            Q(party__name__icontains=search_query) |
            Q(party__company_name__icontains=search_query)
        )
    
    # Order by most recent first
    purchases = purchases.order_by('-invoice_date', '-created_at')
    
    # Pagination
    paginator = Paginator(purchases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get suppliers for filter dropdown
    suppliers = Party.objects.filter(party_type='SUPPLIER', is_active=True)
    
    context = {
        'page_obj': page_obj,
        'suppliers': suppliers,
        'status_choices': Invoice.InvoiceStatus.choices,
        'current_filters': {
            'status': status,
            'supplier': supplier,
            'date_from': date_from,
            'date_to': date_to,
            'q': search_query,
        }
    }
    return render(request, 'core/purchase/purchase_list.html', context)


@login_required
@transaction.atomic
def purchase_create(request):
    """
    Create a new purchase invoice.
    """
    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Save the invoice
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.save()
            
            # Save all items
            total_amount = 0
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.invoice = invoice
                    item.save()
                    total_amount += item.line_total
            
            # Update invoice totals
            invoice.subtotal = total_amount
            invoice.total_amount = total_amount
            invoice.save()
            
            messages.success(request, f'Purchase invoice {invoice.invoice_number} created successfully.')
            return redirect('core:purchase_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseInvoiceForm(initial={'invoice_date': timezone.now().date()})
        formset = PurchaseItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Order',
    }
    return render(request, 'core/purchase/purchase_form.html', context)


@login_required
def purchase_detail(request, pk):
    """
    Display purchase invoice details.
    """
    purchase = get_object_or_404(Invoice, pk=pk, invoice_type='PURCHASE')
    
    context = {
        'purchase': purchase,
        'items': purchase.items.all().select_related('book'),
    }
    return render(request, 'core/purchase/purchase_detail.html', context)


@login_required
@transaction.atomic
def purchase_edit(request, pk):
    """
    Edit a purchase invoice.
    """
    purchase = get_object_or_404(Invoice, pk=pk, invoice_type='PURCHASE')
    
    # Don't allow editing of confirmed invoices
    if purchase.status != 'DRAFT':
        messages.error(request, 'Cannot edit a confirmed or processed purchase invoice.')
        return redirect('core:purchase_detail', pk=pk)
    
    if request.method == 'POST':
        form = PurchaseInvoiceForm(request.POST, instance=purchase)
        formset = PurchaseItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Save the invoice
            invoice = form.save()
            
            # Delete existing items
            invoice.items.all().delete()
            
            # Save new items
            total_amount = 0
            for item_form in formset:
                if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                    item = item_form.save(commit=False)
                    item.invoice = invoice
                    item.save()
                    total_amount += item.line_total
            
            # Update invoice totals
            invoice.subtotal = total_amount
            invoice.total_amount = total_amount
            invoice.save()
            
            messages.success(request, f'Purchase invoice {invoice.invoice_number} updated successfully.')
            return redirect('core:purchase_detail', pk=invoice.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseInvoiceForm(instance=purchase)
        # Create formset with existing items
        initial_data = []
        for item in purchase.items.all():
            initial_data.append({
                'book': item.book,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'discount_percent': item.discount_percent,
                'tax_percent': item.tax_percent,
            })
        formset = PurchaseItemFormSet(initial=initial_data)
    
    context = {
        'form': form,
        'formset': formset,
        'purchase': purchase,
        'title': f'Edit Purchase Order: {purchase.invoice_number}',
    }
    return render(request, 'core/purchase/purchase_form.html', context)


@login_required
def purchase_delete(request, pk):
    """
    Delete a purchase invoice.
    """
    purchase = get_object_or_404(Invoice, pk=pk, invoice_type='PURCHASE')
    
    if purchase.status != 'DRAFT':
        messages.error(request, 'Cannot delete a confirmed or processed purchase invoice.')
        return redirect('core:purchase_detail', pk=pk)
    
    if request.method == 'POST':
        invoice_number = purchase.invoice_number
        purchase.delete()
        messages.success(request, f'Purchase invoice {invoice_number} deleted successfully.')
        return redirect('core:purchase_list')
    
    return render(request, 'core/purchase/purchase_confirm_delete.html', {'purchase': purchase})


@login_required
@transaction.atomic
def purchase_receive(request, pk):
    """
    Process receipt of goods for a purchase invoice.
    """
    purchase = get_object_or_404(Invoice, pk=pk, invoice_type='PURCHASE')
    
    if purchase.status != 'CONFIRMED':
        messages.error(request, 'Only confirmed purchase invoices can be received.')
        return redirect('core:purchase_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            purchase.process_purchase_receipt()
            messages.success(request, f'Purchase {purchase.invoice_number} received and inventory updated.')
        except Exception as e:
            messages.error(request, f'Error processing receipt: {str(e)}')
        
        return redirect('core:purchase_detail', pk=pk)
    
    context = {
        'purchase': purchase,
        'items': purchase.items.all(),
    }
    return render(request, 'core/purchase/purchase_receive.html', context)


@login_required
def purchase_confirm(request, pk):
    """
    Confirm a purchase invoice (move from DRAFT to CONFIRMED).
    """
    purchase = get_object_or_404(Invoice, pk=pk, invoice_type='PURCHASE')
    
    if purchase.status != 'DRAFT':
        messages.error(request, 'This invoice is already confirmed or processed.')
        return redirect('core:purchase_detail', pk=pk)
    
    if request.method == 'POST':
        purchase.status = 'CONFIRMED'
        purchase.save()
        messages.success(request, f'Purchase {purchase.invoice_number} confirmed.')
        return redirect('core:purchase_detail', pk=pk)
    
    return render(request, 'core/purchase/purchase_confirm.html', {'purchase': purchase})