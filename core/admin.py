from django.contrib import admin, messages
from .models import Agent, Testimonial, Service, Credential, Lead, Article, ReviewLink, Agency, Feedback
from django.utils.html import strip_tags
from django.utils import timezone
from .models import Agent, GlobalNewsletter, Subscriber # Adjust Subscriber if named differently
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import PendingAgentOnboarding
from .models import AuditLog
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


@admin.action(description="🚀 BROADCAST NEWSLETTER TO ALL AGENT CLIENTS")
def broadcast_to_all_clients(modeladmin, request, queryset):
    for newsletter in queryset:
        if newsletter.is_sent:
            messages.warning(request, f"'{newsletter.title}' was already broadcasted. You cannot send it twice to prevent spam.")
            continue

        # 1. Get all public agents
        agents = Agent.objects.filter(is_public=True)
        total_emails_sent = 0

        # 2. Loop through every agent
        for agent in agents:
            # 3. Get that specific agent's vaulted clients
            # Adjust 'subscriber_set' to whatever your related_name is in models.py
            clients = Subscriber.objects.filter(agent=agent) 

            # 4. Send white-labeled email to each client
            for client in clients:
                context = {
                    'agent': agent,
                    'client_name': client.name.split()[0], # Grabs first name
                    'content': newsletter.content,
                    'subject': newsletter.subject,
                    'request': request,
                }

                html_content = render_to_string('core/emails/newsletter_wrapper.html', context)
                text_content = strip_tags(html_content)

                msg = EmailMultiAlternatives(
                    subject=newsletter.subject,
                    body=text_content,
                    from_email=f"{agent.name} <updates@skandage.com>", # Appears as the Agent!
                    to=[client.email]
                )
                msg.attach_alternative(html_content, "text/html")
                
                try:
                    msg.send()
                    total_emails_sent += 1
                except Exception as e:
                    print(f"Failed to send to {client.email}: {e}")

        # 5. Mark as sent
        newsletter.is_sent = True
        newsletter.sent_at = timezone.now()
        newsletter.save()

        messages.success(request, f"MASSIVE SUCCESS! Broadcasted '{newsletter.title}' to {total_emails_sent} clients across {agents.count()} agents.")

@admin.register(GlobalNewsletter)
class GlobalNewsletterAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'is_sent', 'sent_at')
    readonly_fields = ('is_sent', 'sent_at')
    actions = [broadcast_to_all_clients]

@admin.register(PendingAgentOnboarding)
class PendingAgentOnboardingAdmin(admin.ModelAdmin):
    # What columns show up in the list view
    list_display = ('full_name', 'agency_name', 'requested_subdomain', 'status', 'created_at')
    
    # Adds a filter sidebar to sort by Pending/Approved or by Agency
    list_filter = ('status', 'agency_name', 'created_at')
    
    # Adds a search bar to easily find a specific agent
    search_fields = ('full_name', 'email', 'phone_number', 'requested_subdomain')
    
    # Protects the timestamp from being accidentally edited
    readonly_fields = ('created_at',)
    
    # Organizes the detail view when you click into an agent
    fieldsets = (
        ('Status', {
            'fields': ('status', 'created_at')
        }),
        ('Personal Details', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Professional Info', {
            'fields': ('agency_name', 'job_title', 'requested_subdomain', 'bio')
        }),
        ('Assets & Links', {
            'fields': ('headshot', 'credentials_upload', 'existing_website', 'linkedin', 'instagram', 'facebook')
        }),
    )

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('feedback_type', 'name', 'email', 'agency_name', 'status', 'created_at')
    list_filter = ('feedback_type', 'status')
    search_fields = ('name', 'email', 'agency_name', 'message')
    readonly_fields = ('name', 'email', 'agency_name', 'feedback_type', 'message', 'created_at')
    list_editable = ('status',)
    ordering = ('-created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # What columns to show in the list view
    list_display = ('agent', 'action', 'target_info', 'ip_address', 'timestamp')
    
    # Adds a sidebar filter to quickly find specific events
    list_filter = ('action', 'timestamp')
    
    # Adds a search bar to look up specific IPs or Agent names
    search_fields = ('agent__name', 'target_info', 'ip_address')
    
    # Make all fields read-only in the detail view
    readonly_fields = ('agent', 'action', 'target_info', 'ip_address', 'timestamp')

    # --- COMPLIANCE LOCKDOWN ---
    # Disable the ability to add, edit, or delete logs via the admin panel
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False