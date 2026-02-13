from django.contrib import admin
from .models import Agent, Testimonial, Service, Credential, Lead, Article, ReviewLink, Agency

# --- INLINE EDITING (Keeps your current workflow) ---
class TestimonialInline(admin.TabularInline):
    model = Testimonial
    extra = 0 # Clean interface, no empty rows by default

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0

class CredentialInline(admin.TabularInline):
    model = Credential
    extra = 0

# --- AGENT ADMIN ---
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    inlines = [ServiceInline, TestimonialInline, CredentialInline]
    # Added 'custom_domain' and 'is_public' to the list view for easy checking
    list_display = ('name', 'company', 'phone_number', 'slug', 'custom_domain', 'is_public')
    search_fields = ('name', 'slug', 'company')
    list_filter = ('company', 'is_public')

# --- NEW: AGENCY ADMIN (This adds the section you were missing) ---
@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'owner', 'created_at')
    search_fields = ('name', 'domain')

# --- OTHER MODELS ---
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'agent', 'created_at')
    list_filter = ('agent',)
    search_fields = ('name', 'email', 'message')

# Registering these allows you to edit them individually if needed
admin.site.register(Article)
admin.site.register(ReviewLink)
# Optional: If you want to see these tables separately as well as inside Agent
admin.site.register(Testimonial)
admin.site.register(Service)
admin.site.register(Credential)