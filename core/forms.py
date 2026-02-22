## core/forms.py (enhanced with more validation)
from django import forms
from django.core.exceptions import ValidationError
from .models import Party
import re

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
        widgets = {
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 1'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address Line 2'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        exclude = ['created_at', 'updated_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input'
            elif not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
            
            # Add placeholders for better UX
            if field_name == 'phone':
                field.widget.attrs['placeholder'] = '+91 98765 43210'
            elif field_name == 'email':
                field.widget.attrs['placeholder'] = 'example@domain.com'
            elif field_name == 'gst_number':
                field.widget.attrs['placeholder'] = '22AAAAA0000A1Z5'
            elif field_name == 'pan_number':
                field.widget.attrs['placeholder'] = 'ABCDE1234F'
            
            if field.required:
                field.widget.attrs['required'] = 'required'
        
        # Pre-fill confirm_email with current email if editing
        if self.instance and self.instance.email:
            self.fields['confirm_email'].initial = self.instance.email
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any spaces, dashes, or parentheses
            phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
            
            # Check if it's a valid Indian phone number (simplified)
            if not re.match(r'^\+?[91]?[6-9]\d{9}$', phone_clean):
                raise ValidationError(
                    "Enter a valid phone number. For Indian numbers, it should start with 6-9 and be 10 digits long."
                )
            return phone_clean
        return phone
    
    def clean_email(self):
        """Validate email and check uniqueness."""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email already exists for another party
            existing = Party.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError("This email is already registered to another party.")
        return email
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        confirm_email = cleaned_data.get('confirm_email')
        
        # Validate email confirmation
        if email and confirm_email and email != confirm_email:
            self.add_error('confirm_email', "Email addresses do not match.")
        
        # Validate GST number format if provided
        gst = cleaned_data.get('gst_number')
        if gst:
            # Basic GST format: 2 digits state code + 10 chars PAN + 1 digit entity + 1 check digit + 1 alphabetic
            if not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}\d[Z]{1}[A-Z\d]{1}$', gst):
                self.add_error('gst_number', 
                    "Invalid GST format. It should be 15 characters: 2 digits (state code) + 10 characters (PAN) + 3 alphanumeric.")
        
        # Validate PAN number format if provided
        pan = cleaned_data.get('pan_number')
        if pan:
            # PAN format: 5 letters + 4 digits + 1 letter
            if not re.match(r'^[A-Z]{5}\d{4}[A-Z]{1}$', pan):
                self.add_error('pan_number', 
                    "Invalid PAN format. It should be 10 characters: 5 letters + 4 digits + 1 letter (all uppercase).")
        
        # Business rule: Suppliers should have PAN/GST more often than customers
        party_type = cleaned_data.get('party_type')
        if party_type == 'SUPPLIER':
            if not gst and not pan:
                self.add_error('gst_number', 
                    "Suppliers should typically have either GST or PAN number for tax compliance.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save to add any pre-save logic."""
        party = super().save(commit=False)
        
        # Auto-capitalize name fields
        if party.name:
            party.name = party.name.title()
        if party.company_name:
            party.company_name = party.company_name.title()
        if party.city:
            party.city = party.city.title()
        
        if commit:
            party.save()
        return party