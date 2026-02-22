# Create your models here.
# core/models.py
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models import Sum

class Party(models.Model):
    """
    Represents a customer or supplier.
    """
    class PartyType(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        SUPPLIER = 'SUPPLIER', 'Supplier'

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
    
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['name', 'party_type'])]
        verbose_name_plural = "Parties"

    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"

    def get_outstanding_balance(self):
        """Calculate total balance: positive = customer owes us, negative = we owe supplier."""
        invoices = self.invoices.filter(status__in=['CONFIRMED', 'OVERDUE', 'PAID'])
        total_invoiced = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        total_paid = invoices.aggregate(total=Sum('paid_amount'))['total'] or 0
        return total_invoiced - total_paid


class Book(models.Model):
    """
    Represents a book in the inventory.
    """
    class BindingType(models.TextChoices):
        HARDCOVER = 'HARDCOVER', 'Hardcover'
        PAPERBACK = 'PAPERBACK', 'Paperback'
        SPIRAL = 'SPIRAL', 'Spiral-bound'
        EBOOK = 'EBOOK', 'E-book'

    title = models.CharField(max_length=500, db_index=True)
    subtitle = models.CharField(max_length=500, blank=True, null=True)
    authors = models.CharField(max_length=500)
    isbn = models.CharField(max_length=13, unique=True, db_index=True)
    publisher = models.CharField(max_length=200, blank=True)
    publication_year = models.IntegerField(blank=True, null=True)
    binding = models.CharField(max_length=20, choices=BindingType.choices, default=BindingType.PAPERBACK)
    
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity_on_hand = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=5)
    
    category = models.CharField(max_length=100, blank=True)
    shelf_location = models.CharField(max_length=50, blank=True)
    is_in_print = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['isbn']),
            models.Index(fields=['title', 'authors']),
        ]

    def __str__(self):
        return f"{self.title} ({self.isbn})"

    def update_stock(self, quantity_change):
        self.quantity_on_hand += quantity_change
        self.save()

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.reorder_level

    @property
    def total_stock_value(self):
        return self.quantity_on_hand * self.cost_price


class Invoice(models.Model):
    """
    Represents a sales or purchase invoice.
    """
    invoice_date = models.DateField()
    payment_method = models.CharField(max_length=50)
    terms_and_conditions = models.TextField(blank=True, null=True)
    due_date = models.DateField(blank=True, null=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    party = models.ForeignKey("Party", on_delete=models.CASCADE)
    notes = models.TextField(blank=True, null=True)

    # other existing fields...
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
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CREDIT)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    # From the Invoice model
def process_purchase_receipt(self):
    # ... validation code ...
    
    for item in self.items.all():
        book = item.book
        # Increase quantity on hand
        book.quantity_on_hand += item.quantity
        
        # Update cost price using weighted average
        if book.cost_price == 0:
            book.cost_price = item.unit_price
        else:
            # Calculate new weighted average cost
            current_value = book.cost_price * (book.quantity_on_hand - item.quantity)
            new_value = item.unit_price * item.quantity
            total_value = current_value + new_value
            book.cost_price = total_value / book.quantity_on_hand
        
        book.save()
    class Meta:
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['party', 'invoice_date']),
        ]

    def __str__(self):
        return f"{self.invoice_number} - {self.party.name}"

    def is_purchase(self):
        return self.invoice_type == self.InvoiceType.PURCHASE

    def update_totals(self):
        items = self.items.all()
        self.subtotal = sum(item.line_total for item in items)
        self.total_amount = self.subtotal - self.discount_amount + self.tax_amount + self.shipping_charges
        self.save()

    def process_purchase_receipt(self):
        if not self.is_purchase():
            raise ValueError("Only purchase invoices can process receipts.")
        
        for item in self.items.all():
            book = item.book
            # Calculate weighted average cost before increasing quantity
            old_qty = book.quantity_on_hand
            new_qty = old_qty + item.quantity
            
            if new_qty > 0:
                total_val = (book.cost_price * old_qty) + (item.unit_price * item.quantity)
                book.cost_price = total_val / new_qty
            
            book.quantity_on_hand = new_qty
            book.save()
        
        self.status = self.InvoiceStatus.PAID
        self.save()


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name='invoice_items')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        discount = (subtotal * self.discount_percent) / 100
        tax = ((subtotal - discount) * self.tax_percent) / 100
        self.line_total = (subtotal - discount) + tax
        super().save(*args, **kwargs)
        self.invoice.update_totals()
        # Add to core/models.py - enhancements for purchase functionality

# Add to the Invoice model's InvoiceType choices (already there from Chapter 3)
# PURCHASE = 'PURCHASE', 'Purchase Invoice'

# Add these methods to the Invoice model
class Invoice(models.Model):
    # ... existing fields ...
    
    def is_purchase(self):
        """Check if this is a purchase invoice."""
        return self.invoice_type == 'PURCHASE'
    
    def is_sales(self):
        """Check if this is a sales invoice."""
        return self.invoice_type == 'SALES'
    
    def process_purchase_receipt(self):
        """
        Process the receipt of goods for a purchase invoice.
        Updates inventory quantities for all items.
        """
        if not self.is_purchase():
            raise ValueError("Can only process purchase receipts for purchase invoices.")
        
        if self.status != 'CONFIRMED':
            raise ValueError("Only confirmed invoices can be processed.")
        
        for item in self.items.all():
            book = item.book
            # Increase quantity on hand
            book.quantity_on_hand += item.quantity
            # Update cost price if it's a new average or if this is the first purchase
            if book.cost_price == 0:
                book.cost_price = item.unit_price
            else:
                # Calculate new weighted average cost
                total_value = (book.cost_price * (book.quantity_on_hand - item.quantity)) + (item.unit_price * item.quantity)
                book.cost_price = total_value / book.quantity_on_hand
            book.save()
        
        self.status = 'PAID'  # Mark as paid (simplified for now)
        self.save()


# Add these methods to the Book model
class Book(models.Model):
    # ... existing fields ...
    
    def update_stock(self, quantity_change):
        """
        Update stock quantity by the given amount (positive for increase, negative for decrease).
        """
        self.quantity_on_hand += quantity_change
        self.save()
    
    def is_available(self, requested_quantity):
        """Check if requested quantity is available."""
        return self.quantity_on_hand >= requested_quantity
    
    @property
    def total_stock_value(self):
        """Calculate total value of stock on hand at cost price."""
        return self.quantity_on_hand * self.cost_price
    
    @property
    def total_sales_value(self):
        """Calculate total value of stock at selling price."""
        return self.quantity_on_hand * self.selling_price
    
    @property
    def potential_profit(self):
        """Calculate potential profit if all stock is sold at current selling price."""
        return self.total_sales_value - self.total_stock_value