from django.contrib import admin
from .models import Agent, Testimonial, Service, Credential, Lead

class TestimonialInline(admin.TabularInline):
    model = Testimonial
    extra = 1

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
class CredentialInline(admin.TabularInline):
    model = Credential
    extra = 1

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    inlines = [ServiceInline, TestimonialInline, CredentialInline]
    list_display = ('name', 'company', 'phone_number', 'slug')
    search_fields = ('name',)

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'agent', 'created_at') # Columns to show
    list_filter = ('agent',) # Filter sidebar
    search_fields = ('name', 'email', 'message') # Search bar