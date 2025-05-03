from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div

from .models import User, DesignationRequest, LeaveRequest

class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'username', 
            'profile_picture', 'bio', 'phone_number'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6'),
                Column('last_name', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            'email',
            'username',
            'profile_picture',
            'bio',
            'phone_number',
            Div(
                Submit('submit', 'Update Profile', css_class='btn btn-primary'),
                css_class='form-group text-right'
            )
        )

class UserPreferencesForm(forms.ModelForm):
    """Form for updating user preferences"""
    
    class Meta:
        model = User
        fields = ['theme_preference']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'theme_preference',
            Div(
                Submit('submit', 'Update Preferences', css_class='btn btn-primary'),
                css_class='form-group text-right'
            )
        )

class DesignationRequestForm(forms.ModelForm):
    """Form for creating designation requests"""
    
    class Meta:
        model = DesignationRequest
        fields = ['requested_role', 'requested_designation', 'reason']
        labels = {
            'requested_role': _('Role'),
            'requested_designation': _('Job Title'),
            'reason': _('Reason for Request'),
        }
        help_texts = {
            'requested_role': _('Select the role you are requesting'),
            'requested_designation': _('Enter your job title or position (e.g., "Senior Developer")'),
            'reason': _('Provide details about why you are requesting this role'),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            'requested_role',
            'requested_designation',
            'reason',
            Div(
                Submit('submit', 'Submit Request', css_class='btn btn-primary'),
                css_class='form-group text-right'
            )
        )
        
        # Exclude SUPERUSER role from the options
        self.fields['requested_role'].choices = [
            choice for choice in self.fields['requested_role'].choices 
            if choice[0] != User.Role.SUPERUSER
        ]

class LeaveRequestForm(forms.ModelForm):
    """Form for creating leave requests"""
    
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            Row(
                Column('start_date', css_class='form-group col-md-6'),
                Column('end_date', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            'reason',
            Div(
                Submit('submit', 'Submit Leave Request', css_class='btn btn-primary'),
                css_class='form-group text-right'
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate that start_date is not in the past
        if start_date and start_date < timezone.now().date():
            self.add_error('start_date', ValidationError(_('Start date cannot be in the past')))
        
        # Validate that end_date is not before start_date
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', ValidationError(_('End date cannot be before start date')))
            
        return cleaned_data 

class UserEditForm(forms.ModelForm):
    """Form for editing user accounts"""
    
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'is_active', 
                 'department', 'role', 'phone_number', 'designation', 'is_approved']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('email', css_class='form-group col-md-6'),
                Column('username', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('first_name', css_class='form-group col-md-6'),
                Column('last_name', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('department', css_class='form-group col-md-6'),
                Column('role', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('phone_number', css_class='form-group col-md-6'),
                Column('designation', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('is_active', css_class='form-group col-md-6'),
                Column('is_approved', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Submit('submit', 'Save Changes', css_class='btn-primary')
        ) 