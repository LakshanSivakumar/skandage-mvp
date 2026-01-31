from django import forms
from .models import Agent, Testimonial, Lead, Article, Credential
from django.contrib.auth.models import User
class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'title', 'company', 'phone_number', 'bio', 'headshot', 'tagline']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'
            }),
            'company': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'
            }),
            'tagline': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pl-10 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 font-mono'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400',
                'rows': 5
            }),
            'headshot': forms.FileInput(attrs={
                'class': 'hidden', # We hide this and use the label trick in HTML
                'id': 'id_headshot'
            }),
        }
    

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['client_name', 'review_text', 'screenshot']
        widgets = {
            'client_name': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 
                'placeholder': 'e.g. Sarah Tan'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 
                'rows': 6,
                'placeholder': 'Paste the full review here...'
            }),
            'screenshot': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'id_screenshot'
            }),
        }

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name', 'email', 'phone', 'message']

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'cover_image', 'content']

class CredentialForm(forms.ModelForm):
    class Meta:
        model = Credential
        fields = ['title', 'issuer', 'year']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. MDRT 2024'}),
            'issuer': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. Million Dollar Round Table'}),
            'year': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'e.g. 2024'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'
            }),
        }
    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        
        # Check if another user ALREADY has this email
        if email and User.objects.filter(email=email).exclude(username=username).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        
        return email