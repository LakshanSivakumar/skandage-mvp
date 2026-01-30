from django import forms
from .models import Agent
from .models import Agent, Testimonial
class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'title', 'company', 'phone_number', 'bio', 'headshot', 'tagline']
        # Styling the widgets to look nice
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'company': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full p-2 border rounded'}),
            'bio': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 4}),
        }
    

class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ['client_name', 'review_text', 'screenshot']
        widgets = {
            'client_name': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm font-medium', 
                'placeholder': 'Client Name'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'w-full p-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm leading-relaxed resize-none', 
                'rows': 10,  # <--- CHANGED TO 10 (Was 3)
                'placeholder': 'Paste the full review or WhatsApp message here...'
            }),
            'screenshot': forms.FileInput(attrs={
                'class': 'block w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition cursor-pointer'
            }),
        }