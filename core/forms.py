from django import forms
from .models import Agent, Testimonial, Lead, Article, Credential, Service, Agency, AgencyImage, AgencyReview
from django.contrib.auth.models import User

class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'title', 'company', 'phone_number', 'bio', 'headshot', 'tagline', 'theme', 'layout','linkedin', 'instagram', 'facebook', 'disclaimer', 'calendly_link']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'company': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'tagline': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pl-10 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500 font-mono'}),
            'linkedin': forms.URLInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pl-10 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'https://linkedin.com/in/...'}),
            'instagram': forms.URLInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pl-10 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'https://instagram.com/...'}),
            'facebook': forms.URLInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pl-10 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'https://facebook.com/...'}),
            'bio': forms.Textarea(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 5}),
            'headshot': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_headshot'}),
            'theme': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'layout': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition'}),
            'disclaimer': forms.Textarea(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500 text-sm', 'rows': 4}),
            'calendly_link': forms.URLInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 pl-10 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'https://calendly.com/...'}),

        }
    
class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['title', 'client_name', 'review_text', 'screenshot', 'video', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'Headline (e.g. Best Advisor!)'}),
            'client_name': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'e.g. Sarah Tan'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 6, 'placeholder': 'Paste the full review here...'}),
            
            # THE FIX: Explicitly set the accept attributes and unique IDs
            'screenshot': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_screenshot', 'accept': 'image/*'}),
            'video': forms.FileInput(attrs={'class': 'hidden', 'id': 'id_video', 'accept': 'video/mp4,video/quicktime,video/*'}),
            
            'is_published': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-blue-600 rounded focus:ring-blue-500 border-gray-300 dark:border-slate-600 dark:bg-slate-700'}),
        }

class ClientSubmissionForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        # THE FIX: Add screenshot and video back to the fields list!
        fields = ['title', 'review_text', 'screenshot', 'video']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500 font-bold', 'placeholder': 'Headline (e.g. "Great Service")'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 6, 'placeholder': 'Share your experience...'}),
            
            # Ensure the client-facing form also filters properly
            'screenshot': forms.FileInput(attrs={'accept': 'image/*', 'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-slate-700 dark:file:text-slate-300'}),
            'video': forms.FileInput(attrs={'accept': 'video/mp4,video/quicktime,video/*', 'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-slate-700 dark:file:text-slate-300'}),
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
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'e.g. MDRT 2024'}),
            'issuer': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'e.g. Million Dollar Round Table'}),
            'year': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'e.g. 2024'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
            'email': forms.EmailInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
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
            'title': forms.TextInput(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'e.g. Retirement Planning'}),
            'icon': forms.Select(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition'}),
            'description': forms.Textarea(attrs={'class': 'w-full bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 3, 'placeholder': 'Briefly explain this service...'}),
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
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'domain': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none', 'readonly': 'readonly'}),
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full rounded cursor-pointer'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full rounded cursor-pointer'}),
            'hero_headline': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'hero_subheadline': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 2}),
            'about_text': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 4, 'placeholder': 'Tell your agency story...'}),
            'values_text': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 3, 'placeholder': 'e.g. Integrity, Excellence, Family...'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 2}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500'}),
        }

class AgencyImageForm(forms.ModelForm):
    class Meta:
        model = AgencyImage
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'Optional caption'})
        }

class AgencyReviewForm(forms.ModelForm):
    class Meta:
        model = AgencyReview
        fields = ['fc_name', 'fc_role', 'fc_photo', 'review_text']
        widgets = {
            'fc_name': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'Name'}),
            'fc_role': forms.TextInput(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'placeholder': 'Title (e.g. Senior Director)'}),
            'review_text': forms.Textarea(attrs={'class': 'w-full p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900/50 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition placeholder-slate-400 dark:placeholder-slate-500', 'rows': 3}),
        }