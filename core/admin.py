from django.contrib import admin

# Register your models here.
# core/admin.py
from django.contrib import admin
from .models import Party, Book, Invoice, InvoiceItem

@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'party_type', 'phone', 'email', 'city', 'is_active']
    list_filter = ['party_type', 'is_active', 'country']
    search_fields = ['name', 'company_name', 'phone', 'email']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('party_type', 'name', 'company_name', 'is_active')
        }),
        ('Contact Details', {
            'fields': ('phone', 'email', ('address_line1', 'address_line2'), 
                      ('city', 'state'), ('postal_code', 'country'))
        }),
        ('Tax Information', {
            'fields': ('gst_number', 'pan_number', 'credit_limit'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'authors', 'isbn', 'selling_price', 'quantity_on_hand', 'is_low_stock']
    list_filter = ['binding', 'publisher', 'is_in_print', 'is_active']
    search_fields = ['title', 'authors', 'isbn', 'publisher']
    list_editable = ['selling_price', 'quantity_on_hand']
    readonly_fields = ['created_at', 'updated_at', 'profit_margin']
    fieldsets = (
        ('Book Details', {
            'fields': ('title', 'subtitle', 'authors', 'isbn')
        }),
        ('Publication', {
            'fields': ('publisher', 'publication_year', 'binding')
        }),
        ('Pricing', {
            'fields': ('mrp', 'selling_price', 'cost_price', 'profit_margin')
        }),
        ('Inventory', {
            'fields': ('quantity_on_hand', 'reorder_level', 'shelf_location', 'is_in_print')
        }),
        ('Additional', {
            'fields': ('category', 'notes', 'is_active'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class InvoiceItemInline(admin.TabularInline):
    """Inline editing for invoice items"""
    model = InvoiceItem
    extra = 1
    fields = ['book', 'quantity', 'unit_price', 'discount_percent', 'line_total']
    readonly_fields = ['line_total']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'party', 'invoice_type', 'invoice_date', 
                   'total_amount', 'status', 'balance_due']
    list_filter = ['invoice_type', 'status', 'payment_method', 'invoice_date']
    search_fields = ['invoice_number', 'party__name']
    readonly_fields = ['subtotal', 'total_amount', 'balance_due', 'created_at', 'updated_at']
    inlines = [InvoiceItemInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'invoice_type', 'status', 'party')
        }),
        ('Dates', {
            'fields': ('invoice_date', 'due_date')
        }),
        ('Financial Summary', {
            'fields': ('subtotal', 'discount_amount', 'tax_amount', 
                      'shipping_charges', 'total_amount', 'paid_amount', 'balance_due')
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_reference')
        }),
        ('Additional', {
            'fields': ('notes', 'terms_and_conditions', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'book', 'quantity', 'unit_price', 'line_total']
    list_filter = ['invoice__invoice_type']
    search_fields = ['book__title', 'invoice__invoice_number']
    readonly_fields = ['line_total']
