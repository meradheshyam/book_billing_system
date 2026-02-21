from django.db import models

# Create your models here.
# core/models.py
from django.db import models
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone

class Party(models.Model):
    """
    Represents a customer or supplier.
    """
    class PartyType(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        SUPPLIER = 'SUPPLIER', 'Supplier'
    
    # Basic Information
    party_type = models.CharField(
        max_length=10,
        choices=PartyType.choices,
        default=PartyType.CUSTOMER,
        help_text="Type of party: Customer or Supplier"
    )
    name = models.CharField(max_length=200, db_index=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="India")
    
    # Tax and Business Information
    gst_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        help_text="Goods and Services Tax Number (for Indian businesses)"
    )
    pan_number = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        help_text="Permanent Account Number (for Indian businesses)"
    )
    credit_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00,
        help_text="Maximum credit allowed for this party"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name', 'party_type']),
        ]
        verbose_name_plural = "Parties"
    
    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"
    
    def get_outstanding_balance(self):
        """
        Calculate the total outstanding balance for this party.
        This will be implemented later when we have invoices.
        """
        # Placeholder for future implementation
        return 0
# core/models.py (continued)

class Book(models.Model):
    """
    Represents a book in the inventory.
    """
    class BindingType(models.TextChoices):
        HARDCOVER = 'HARDCOVER', 'Hardcover'
        PAPERBACK = 'PAPERBACK', 'Paperback'
        SPIRAL = 'SPIRAL', 'Spiral-bound'
        EBOOK = 'EBOOK', 'E-book'
    
    # Basic Information
    title = models.CharField(max_length=500, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True, null=True)
    authors = models.CharField(
        max_length=500, 
        help_text="Multiple authors can be separated by commas"
    )
    
    # Publishing Details
    isbn = models.CharField(
        max_length=13, 
        unique=True, 
        db_index=True,
        help_text="International Standard Book Number (10 or 13 digits)"
    )
    publisher = models.CharField(max_length=200, blank=True)
    publication_year = models.IntegerField(blank=True, null=True)
    binding = models.CharField(
        max_length=20,
        choices=BindingType.choices,
        default=BindingType.PAPERBACK
    )
    
    # Pricing and Inventory
    mrp = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Maximum Retail Price"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Current selling price"
    )
    cost_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Purchase cost from supplier",
        default=0.00
    )
    quantity_on_hand = models.IntegerField(default=0)
    reorder_level = models.IntegerField(
        default=5,
        help_text="Minimum quantity before reordering"
    )
    
    # Additional Information
    category = models.CharField(max_length=100, blank=True)
    shelf_location = models.CharField(max_length=50, blank=True)
    is_in_print = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['isbn']),
            models.Index(fields=['title', 'authors']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.isbn})"
    
    @property
    def is_low_stock(self):
        """Check if book quantity is below reorder level."""
        return self.quantity_on_hand <= self.reorder_level
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage."""
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0
    # core/models.py (continued)

class Invoice(models.Model):
    """
    Represents a sales or purchase invoice.
    """
    class InvoiceType(models.TextChoices):
        SALES = 'SALES', 'Sales Invoice'
        PURCHASE = 'PURCHASE', 'Purchase Invoice'
        SALES_RETURN = 'SALES_RETURN', 'Sales Return'
        PURCHASE_RETURN = 'PURCHASE_RETURN', 'Purchase Return'
    
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PROFORMA = 'PROFORMA', 'Proforma'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'
    
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Credit/Debit Card'
        UPI = 'UPI', 'UPI'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'
        CREDIT = 'CREDIT', 'Credit (Account)'
    
    # Invoice Identification
    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    invoice_type = models.CharField(
        max_length=20,
        choices=InvoiceType.choices,
        default=InvoiceType.SALES
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    
    # Relationships
    party = models.ForeignKey(
        Party,
        on_delete=models.PROTECT,
        related_name='invoices',
        help_text="Customer for sales, Supplier for purchases"
    )
    
    # Dates
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    
    # Financial Details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Payment
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CREDIT
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    
    # User Tracking
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices_created'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['party', 'invoice_date']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number} - {self.party.name}"
    
    @property
    def balance_due(self):
        """Calculate remaining balance."""
        return self.total_amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        if self.due_date and self.status in ['CONFIRMED', 'OVERDUE']:
            return timezone.now().date() > self.due_date and self.balance_due > 0
        return False
    
    def update_totals(self):
        """
        Recalculate all totals based on invoice items.
        This will be called when items are added/removed.
        """
        items = self.items.all()
        self.subtotal = sum(item.line_total for item in items)
        # Tax and discount logic will be added later
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount + self.shipping_charges
        self.save()
        # core/models.py (continued)

class InvoiceItem(models.Model):
    """
    Represents a single line item on an invoice.
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name='invoice_items'
    )
    
    # Item Details
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Discount percentage applied to this item"
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    tax_percent = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00
    )
    line_total = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.quantity} x {self.book.title}"
    
    def save(self, *args, **kwargs):
        """
        Override save to calculate line totals.
        """
        # Calculate line total
        subtotal = self.quantity * self.unit_price
        self.discount_amount = (subtotal * self.discount_percent) / 100
        after_discount = subtotal - self.discount_amount
        self.tax_amount = (after_discount * self.tax_percent) / 100
        self.line_total = after_discount + self.tax_amount
        
        super().save(*args, **kwargs)
        
        # Update the parent invoice totals
        self.invoice.update_totals()