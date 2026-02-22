# core/views.py - Refactored with Class-Based Views
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from .models import Party
from .forms import PartyForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages  # Fixes "messages" error
from django.utils import timezone

from .models import Party, Invoice, InvoiceItem
from .forms import PartyForm

class PartyListView(ListView):
    """
    Display list of parties with search and filter.
    """
    model = Party
    template_name = 'core/party_list.html'
    context_object_name = 'parties'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get search query and filter from request
        query = self.request.GET.get('q', '')
        party_type = self.request.GET.get('type', '')
        
        # Apply search filter
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(company_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query) |
                Q(city__icontains=query)
            )
        
        # Apply party type filter
        if party_type:
            queryset = queryset.filter(party_type=party_type)
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['party_type'] = self.request.GET.get('type', '')
        context['party_types'] = Party.PartyType.choices
        return context

class PartyDetailView(DetailView):
    """
    Display party details.
    """
    model = Party
    template_name = 'core/party_detail.html'
    context_object_name = 'party'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add recent invoices (will be implemented later)
        context['recent_invoices'] = []
        return context

class PartyCreateView(SuccessMessageMixin, CreateView):
    """
    Create a new party.
    """
    model = Party
    form_class = PartyForm
    template_name = 'core/party_form.html'
    success_url = reverse_lazy('core:party_list')
    success_message = "Party '%(name)s' created successfully."
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Party'
        return context

class PartyUpdateView(SuccessMessageMixin, UpdateView):
    """
    Update an existing party.
    """
    model = Party
    form_class = PartyForm
    template_name = 'core/party_form.html'
    success_message = "Party '%(name)s' updated successfully."
    
    def get_success_url(self):
        return reverse_lazy('core:party_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit Party: {self.object.name}'
        return context

class PartyDeleteView(DeleteView):
    """
    Delete a party.
    """
    model = Party
    success_url = reverse_lazy('core:party_list')
    template_name = 'core/party_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        party = self.get_object()
        messages.success(request, f'Party "{party.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)
    # core/views.py (add this function)
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Invoice, InvoiceItem

def party_statement(request, pk):
    """
    Generate a statement of all transactions for a party.
    """
    party = get_object_or_404(Party, pk=pk)
    
    # Get date range from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    invoices = party.invoices.all()
    
    # Apply date filters
    if start_date:
        invoices = invoices.filter(invoice_date__gte=start_date)
    if end_date:
        invoices = invoices.filter(invoice_date__lte=end_date)
    
    # Order by date
    invoices = invoices.order_by('-invoice_date')
    
    # Calculate summary statistics
    summary = {
        'total_invoices': invoices.count(),
        'total_sales': invoices.filter(
            invoice_type='SALES'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_purchases': invoices.filter(
            invoice_type='PURCHASE'
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_paid': invoices.aggregate(total=Sum('paid_amount'))['total'] or 0,
        'outstanding': party.get_outstanding_balance(),
    }
    
    context = {
        'party': party,
        'invoices': invoices,
        'summary': summary,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/party_statement.html', context)