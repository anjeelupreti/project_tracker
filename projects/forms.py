from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div

from .models import Department, Project, Task, TaskComment, TaskAttachment, ProjectAttachment, ProjectUpdate, TaskUpdate, ChatMessage
from accounts.models import User

class DepartmentForm(forms.ModelForm):
    """Form for creating and updating departments"""
    
    class Meta:
        model = Department
        fields = ['name', 'description', 'head']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'description',
            'head',
            Div(
                Submit('submit', 'Save Department', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        # Filter users to only include admins and team leads for department head
        self.fields['head'].queryset = User.objects.filter(
            is_approved=True
        ).exclude(role=User.Role.MEMBER).order_by('first_name', 'last_name')
        self.fields['head'].empty_label = "Select a department head (optional)"

class ProjectForm(forms.ModelForm):
    """Form for creating and updating projects"""
    
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'department', 'lead', 'status',
            'start_date', 'end_date', 'priority'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'description',
            Row(
                Column('department', css_class='form-group col-md-6'),
                Column('lead', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('start_date', css_class='form-group col-md-6'),
                Column('end_date', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('status', css_class='form-group col-md-6'),
                Column('priority', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Div(
                Submit('submit', 'Save Project', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        # Filter users to only include approved users
        self.fields['lead'].queryset = User.objects.filter(
            is_approved=True
        ).order_by('first_name', 'last_name')
        
        # If user is not admin, restrict department and lead choices
        if self.user and not (self.user.is_admin or self.user.is_superuser):
            if self.user.is_team_lead:
                # Team leads can only assign themselves as lead
                self.fields['lead'].queryset = User.objects.filter(id=self.user.id)
                self.fields['lead'].initial = self.user
                self.fields['lead'].disabled = True
            
            # If user has a department, pre-select it
            if self.user.department:
                self.fields['department'].initial = self.user.department

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate that end_date is not before start_date
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', ValidationError(_('End date cannot be before start date')))
            
        return cleaned_data

class TaskForm(forms.ModelForm):
    """Form for creating and updating tasks"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'project', 'assignee', 'status',
            'priority', 'due_date', 'estimated_hours'
        ]
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'title',
            'description',
            Row(
                Column('project', css_class='form-group col-md-6'),
                Column('assignee', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('status', css_class='form-group col-md-6'),
                Column('priority', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('due_date', css_class='form-group col-md-6'),
                Column('estimated_hours', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Div(
                Submit('submit', 'Save Task', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        # Filter projects based on user access
        if self.user and not (self.user.is_admin or self.user.is_superuser):
            if self.user.is_team_lead:
                # Team leads can create tasks for their led projects
                self.fields['project'].queryset = Project.objects.filter(
                    lead=self.user
                ).order_by('name')
            else:
                # Regular members can only create tasks for projects they're part of
                self.fields['project'].queryset = Project.objects.filter(
                    members=self.user
                ).order_by('name')
            
            # If there's only one project available, select it by default
            if self.fields['project'].queryset.count() == 1:
                self.fields['project'].initial = self.fields['project'].queryset.first()
        
        # Allow selection of users from the project as assignees
        if self.instance and self.instance.pk and self.instance.project:
            self.fields['assignee'].queryset = self.instance.project.members.all().order_by(
                'first_name', 'last_name'
            )
        else:
            # Initially, no project selected, so no assignee options
            self.fields['assignee'].queryset = User.objects.none()
            
        # If current user is a member, default assignee to self
        if self.user and self.user.role == User.Role.MEMBER:
            self.fields['assignee'].initial = self.user

    def clean(self):
        cleaned_data = super().clean()
        due_date = cleaned_data.get('due_date')
        
        # Validate due date is not in the past for new tasks
        if due_date and not self.instance.pk and due_date < timezone.now().date():
            self.add_error('due_date', ValidationError(_('Due date cannot be in the past for new tasks')))
            
        return cleaned_data

class TaskAssignForm(forms.ModelForm):
    """Form for assigning tasks to users"""
    
    class Meta:
        model = Task
        fields = ['assignee']
        
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'assignee',
            Div(
                Submit('submit', 'Assign Task', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        # Filter assignee to project members
        if self.project:
            self.fields['assignee'].queryset = self.project.members.all().order_by(
                'first_name', 'last_name'
            )

class TaskCommentForm(forms.ModelForm):
    """Form for adding comments to tasks"""
    
    class Meta:
        model = TaskComment
        fields = ['content']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            'content',
            Div(
                Submit('submit', 'Add Comment', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        self.fields['content'].widget.attrs.update({
            'placeholder': 'Write a comment...',
            'rows': 3
        })

class TaskAttachmentForm(forms.ModelForm):
    """Form for adding attachments to tasks"""
    
    class Meta:
        model = TaskAttachment
        fields = ['file', 'filename']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.layout = Layout(
            'file',
            'filename',
            Div(
                Submit('submit', 'Upload Attachment', css_class='btn btn-primary'),
                css_class='text-end'
            )
        )
        
        self.fields['filename'].required = False
        self.fields['filename'].help_text = "Leave blank to use the original filename"

class ProjectAttachmentForm(forms.ModelForm):
    """Form for adding attachments to projects"""
    
    class Meta:
        model = ProjectAttachment
        fields = ['file', 'filename', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_tag = True
        self.helper.layout = Layout(
            'file',
            'filename',
            'description',
            Submit('submit', 'Upload Attachment', css_class='btn btn-primary')
        )
        self.fields['filename'].required = False 

class ProjectUpdateForm(forms.ModelForm):
    """Form for creating project updates"""
    
    class Meta:
        model = ProjectUpdate
        fields = ['update_type', 'title', 'content', 'completion_percentage', 'new_estimated_date']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5}),
            'new_estimated_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            'update_type',
            'title',
            'content',
            'completion_percentage',
            'new_estimated_date',
            Submit('submit', 'Post Update', css_class='btn btn-primary')
        )
        
        # Make some fields optional based on update type
        self.fields['completion_percentage'].required = False
        self.fields['new_estimated_date'].required = False
        
class TaskUpdateForm(forms.ModelForm):
    """Form for creating task updates"""
    
    class Meta:
        model = TaskUpdate
        fields = ['content', 'hours_spent', 'completion_percentage']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'
        self.helper.layout = Layout(
            'content',
            Row(
                Column('hours_spent', css_class='form-group col-md-6'),
                Column('completion_percentage', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Submit('submit', 'Post Update', css_class='btn btn-primary')
        ) 

class ChatMessageForm(forms.ModelForm):
    """Form for sending chat messages in a project"""
    
    class Meta:
        model = ChatMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Type your message...'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Row(
                Column('message', css_class='form-group col-md-10'),
                Column(Submit('submit', 'Send', css_class='btn btn-primary'), css_class='form-group col-md-2 d-flex align-items-end'),
                css_class='form-row'
            ),
        ) 