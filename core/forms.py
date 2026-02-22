import re
from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory, BaseFormSet
from .models import Party, Invoice, InvoiceItem, Book

class PartyForm(forms.ModelForm):
    """
    Enhanced form for creating and editing parties with business logic.
    """
    confirm_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label="Confirm Email"
    )
    
    class Meta:
        model = Party
        fields = '__all__'
        exclude = ['created_at', 'updated_at']
        widgets = {
            'address_line1': forms.TextInput(attrs={'placeholder': 'Address Line 1'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Address Line 2'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes and placeholders dynamically
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input'
            elif not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
            
            # Specific placeholders for better UX
            placeholders = {
                'phone': '+91 xxxxx xxxxx',
                'email': 'example@domain.com',
                'gst_number': '22AAAAA0000A1Z5',
                'pan_number': 'ABCDE1234F'
            }
            if field_name in placeholders:
                field.widget.attrs['placeholder'] = placeholders[field_name]
            
            if field.required:
                field.widget.attrs['required'] = 'required'
        
        # Pre-fill confirm_email if editing
        if self.instance and self.instance.email:
            self.fields['confirm_email'].initial = self.instance.email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
            if not re.match(r'^\+?[91]?[6-9]\d{9}$', phone_clean):
                raise ValidationError("Enter a valid Indian phone number (10 digits starting with 6-9).")
            return phone_clean
        return phone
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            existing = Party.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("This email is already registered to another party.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        gst = cleaned_data.get('gst_number')
        pan = cleaned_data.get('pan_number')
        party_type = cleaned_data.get('party_type')
        
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Email addresses do not match.")
        
        if gst and not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z]{1}[A-Z\d]{1}$', gst):
            self.add_error('gst_number', "Invalid GST format (15 characters).")
            
        if pan and not re.match(r'^[A-Z]{5}\d{4}[A-Z]{1}$', pan):
            self.add_error('pan_number', "Invalid PAN format (e.g., ABCDE1234F).")
        
        if party_type == 'SUPPLIER' and not gst and not pan:
            self.add_error('gst_number', "Suppliers typically require GST or PAN for tax compliance.")
            
        return cleaned_data

    def save(self, commit=True):
        party = super().save(commit=False)
        # Standardize formatting
        for attr in ['name', 'company_name', 'city']:
            val = getattr(party, attr)
            if val: setattr(party, attr, val.title())
        
        if commit: party.save()
        return party

# --- Purchase Management Forms ---

class PurchaseInvoiceForm(forms.ModelForm):
    """Form for creating purchase orders/invoices."""
    class Meta:
        model = Invoice
        fields = ['party', 'invoice_date', 'due_date', 'payment_method', 
                  'payment_reference', 'notes', 'terms_and_conditions']
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'terms_and_conditions': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['party'].queryset = Party.objects.filter(party_type='SUPPLIER', is_active=True)
        self.fields['party'].label = "Supplier"
        
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        invoice = super().save(commit=False)
        invoice.invoice_type = Invoice.InvoiceType.PURCHASE
        invoice.status = Invoice.InvoiceStatus.DRAFT
        
        if not invoice.invoice_number:
            last = Invoice.objects.filter(invoice_type=Invoice.InvoiceType.PURCHASE).order_by('-id').first()
            new_num = (int(last.invoice_number.split('-')[-1]) + 1) if last else 1
            invoice.invoice_number = f"PO-{new_num:06d}"
        
        if commit: invoice.save()
        return invoice

class PurchaseItemForm(forms.ModelForm):
    """Form for individual purchase line items."""
    class Meta:
        model = InvoiceItem
        fields = ['book', 'quantity', 'unit_price', 'discount_percent', 'tax_percent']
        widgets = {
            'book': forms.Select(attrs={'class': 'form-control select2-book'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control', 'max': '100'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'max': '100'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(is_active=True).order_by('title')
        self.fields['book'].label_from_instance = lambda obj: f"{obj.title} (ISBN: {obj.isbn})"

class BasePurchaseItemFormSet(BaseFormSet):
    """Validation to prevent duplicate books in one invoice."""
    def clean(self):
        if any(self.errors): return
        books = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form): continue
            book = form.cleaned_data.get('book')
            if book:
                if book in books:
                    raise forms.ValidationError(f"Duplicate entry: {book.title} is listed twice.")
                books.append(book)

PurchaseItemFormSet = formset_factory(
    PurchaseItemForm,
    formset=BasePurchaseItemFormSet,
    extra=1,
    can_delete=True
)# core/forms.py - Add purchase-specific forms

from django.forms import formset_factory, BaseFormSet
from .models import Invoice, InvoiceItem, Book, Party

class PurchaseInvoiceForm(forms.ModelForm):
    """
    Form for creating purchase invoices.
    """
    class Meta:
        model = Invoice
        fields = ['party', 'invoice_date', 'due_date', 'payment_method', 
                  'payment_reference', 'notes', 'terms_and_conditions']
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'terms_and_conditions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter parties to show only suppliers
        self.fields['party'].queryset = Party.objects.filter(
            party_type='SUPPLIER', 
            is_active=True
        )
        self.fields['party'].label = "Supplier"
        
        # Add Bootstrap classes
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
    
    def save(self, commit=True):
        invoice = super().save(commit=False)
        invoice.invoice_type = 'PURCHASE'
        invoice.status = 'DRAFT'
        
        # Generate invoice number
        if not invoice.invoice_number:
            last_invoice = Invoice.objects.filter(invoice_type='PURCHASE').order_by('-id').first()
            if last_invoice:
                last_number = int(last_invoice.invoice_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            invoice.invoice_number = f"PO-{new_number:06d}"
        
        if commit:
            invoice.save()
        return invoice


class PurchaseItemForm(forms.ModelForm):
    """
    Form for individual purchase line items.
    """
    class Meta:
        model = InvoiceItem
        fields = ['book', 'quantity', 'unit_price', 'discount_percent', 'tax_percent']
        widgets = {
            'book': forms.Select(attrs={'class': 'form-control select2-book'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control quantity-input', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price-input', 'step': '0.01', 'min': '0'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'form-control discount-input', 'step': '0.01', 'min': '0', 'max': '100'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control tax-input', 'step': '0.01', 'min': '0', 'max': '100'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active books
        self.fields['book'].queryset = Book.objects.filter(is_active=True).order_by('title')
        self.fields['book'].label_from_instance = lambda obj: f"{obj.title} ({obj.isbn}) - ₹{obj.mrp}"
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')
        
        if quantity and quantity < 1:
            self.add_error('quantity', "Quantity must be at least 1.")
        
        if unit_price and unit_price < 0:
            self.add_error('unit_price', "Price cannot be negative.")
        
        return cleaned_data


class BasePurchaseItemFormSet(BaseFormSet):
    """
    Custom formset for purchase items with additional validation.
    """
    def clean(self):
        if any(self.errors):
            return
        
        books = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            
            book = form.cleaned_data.get('book')
            if book in books:
                raise forms.ValidationError("Each book can only appear once in a purchase invoice.")
            books.append(book)


# Create the formset for multiple items
PurchaseItemFormSet = formset_factory(
    PurchaseItemForm,
    formset=BasePurchaseItemFormSet,
    extra=1,
    can_delete=True,
    max_num=50
)