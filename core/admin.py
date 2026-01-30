from django.contrib import admin
from .models import Agent, Testimonial, Service, Credential

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