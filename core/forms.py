from django import forms
from .models import Agent, Testimonial, Lead, Article, Credential, Service, Agency, AgencyImage, AgencyReview
from django.contrib.auth.models import User

class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'title', 'company', 'phone_number', 'bio', 'headshot', 'tagline', 'theme', 'layout','linkedin', 'instagram', 'facebook', 'disclaimer']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'}),
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'}),
            'company': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'}),
            'tagline': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pl-10 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 font-mono'}),
            'linkedin': forms.URLInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pl-10 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 'placeholder': 'https://linkedin.com/in/...'}),
            'instagram': forms.URLInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pl-10 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 'placeholder': 'https://instagram.com/...'}),
            'facebook': forms.URLInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 pl-10 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 'placeholder': 'https://facebook.com/...'}),
            'bio': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400', 'rows': 5}),
            'headshot': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_headshot'}),
            'theme': forms.Select(attrs={'class': 'w-full p-3 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'layout': forms.Select(attrs={'class': 'w-full p-3 border border-gray-300 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'disclaimer': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 text-sm', 'rows': 4}),
        }
    
class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['title', 'client_name', 'review_text', 'screenshot', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400', 'placeholder': 'Headline (e.g. Best Advisor!)'}),
            'client_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400', 'placeholder': 'e.g. Sarah Tan'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400', 'rows': 6, 'placeholder': 'Paste the full review here...'}),
            # CRITICAL FIX: Ensure ID matches the one used in the template's onClick
            'screenshot': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_screenshot'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-blue-600 rounded focus:ring-blue-500 border-gray-300'}),
        }

class ClientSubmissionForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['title', 'review_text']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 font-bold', 'placeholder': 'Headline (e.g. "Great Service")'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400', 'rows': 6, 'placeholder': 'Share your experience...'}),
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
            'username': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
            'email': forms.EmailInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
        }
    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and User.objects.filter(email=email).exclude(username=username).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return email
    
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'icon', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition', 'placeholder': 'e.g. Retirement Planning'}),
            'icon': forms.Select(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition', 'rows': 3, 'placeholder': 'Briefly explain this service...'}),
        }

class AgencySiteForm(forms.ModelForm):
    class Meta:
        model = Agency
        fields = [
            'name', 'domain', 'primary_color', 'secondary_color', 
            'hero_headline', 'hero_subheadline', 'hero_image', 'logo',
            'about_text', 'values_text',
            'email', 'phone', 'address', 'whatsapp_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'domain': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl', 'readonly': 'readonly'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full rounded cursor-pointer'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full rounded cursor-pointer'}),
            'hero_headline': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl font-bold'}),
            'hero_subheadline': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-xl', 'rows': 2}),
            'about_text': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-xl', 'rows': 4, 'placeholder': 'Tell your agency story...'}),
            'values_text': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-xl', 'rows': 3, 'placeholder': 'e.g. Integrity, Excellence, Family...'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border rounded-xl', 'rows': 2}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-xl'}),
        }

class AgencyImageForm(forms.ModelForm):
    class Meta:
        model = AgencyImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Optional caption'})
        }

class AgencyReviewForm(forms.ModelForm):
    class Meta:
        model = AgencyReview
        fields = ['fc_name', 'fc_role', 'fc_photo', 'review_text']
        widgets = {
            'fc_name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Name'}),
            'fc_role': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Title (e.g. Senior Director)'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
        }