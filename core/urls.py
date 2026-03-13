from django.urls import path, include
from . import views
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import AgentSitemap
from django.contrib.auth import views as auth_views # <--- ADDED THIS IMPORT

# Define the dictionary of sitemaps
sitemaps = {
    'agents': AgentSitemap,
}

urlpatterns = [
    # --- PUBLIC DOMAIN ROUTER ---
    path('', views.domain_router, name='home'),
    path('expertise/', views.domain_expertise, name='domain_expertise'), 
    path('bio/', views.domain_bio, name='domain_bio'), 
    path('letters/', views.domain_letters, name='domain_letters'),
    path('feedback/', views.feedback_submit, name='feedback'), 
    path('api/agent-autocomplete/', views.api_agent_autocomplete, name='api_agent_autocomplete'), 
    
    path('accounts/login/', views.custom_login, name='login'),
    path('accounts/otp-verify/', views.otp_verify, name='otp_verify'),

    # ==========================================
    # --- CUSTOM FORGOT PASSWORD FLOW ---
    # ==========================================
    path('accounts/password_reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset_form.html',
        html_email_template_name='core/emails/password_reset_html_email.html',
        email_template_name='core/emails/password_reset_email.html', 
    ), name='password_reset'),
    
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Default auth URLs
    path('accounts/', include('django.contrib.auth.urls')),
    
    # --- PUBLIC AGENT PAGES ---
    path('agent/<slug:slug>/', views.agent_profile, name='agent_profile'),
    path('read/<slug:slug>/', views.article_detail, name='article_detail'),

    # --- DASHBOARD (Protected) ---
    path('dashboard/', views.dashboard_stats, name='dashboard'), 
    path('dashboard/profile/', views.manage_profile, name='manage_profile'),
    path('dashboard/articles/', views.manage_articles, name='manage_articles'),
    path('dashboard/testimonials/', views.manage_testimonials, name='manage_testimonials'),
    path('webhook/telegram/', views.telegram_webhook, name='telegram_webhook'),

    # --- ACTIONS: Articles ---
    path('dashboard/article/new/', views.create_article, name='create_article'),
    path('dashboard/article/edit/<int:pk>/', views.edit_article, name='edit_article'),
    path('dashboard/article/<int:pk>/email-all/', views.email_article_to_all, name='email_article_to_all'),
    path('dashboard/article/<int:pk>/whatsapp-all/', views.whatsapp_article_to_all, name='whatsapp_article_to_all'),
    
    # --- ACTIONS: Credentials ---
    path('dashboard/credential/add/', views.add_credential, name='add_credential'),
    path('dashboard/credential/delete/<int:pk>/', views.delete_credential, name='delete_credential'),
    path('dashboard/credential/edit/<int:pk>/', views.edit_credential, name='edit_credential'),
    path('dashboard/credentials/reorder/', views.reorder_credentials, name='reorder_credentials'),

    # --- ACTIONS: Testimonials ---
    path('dashboard/testimonial/add/', views.add_testimonial, name='add_testimonial'),     
    path('dashboard/testimonial/delete/<int:pk>/', views.delete_testimonial, name='delete_testimonial'), 
    path('dashboard/testimonial/edit/<int:pk>/', views.edit_testimonial, name='edit_testimonial'), 
    path('dashboard/testimonial/toggle-feature/<int:pk>/', views.toggle_testimonial_feature, name='toggle_testimonial_feature'),
    path('dashboard/testimonials/import/', views.import_testimonials, name='import_testimonials'),
    path('dashboard/testimonials/generate-link/', views.generate_review_link, name='generate_review_link'),

    # --- DASHBOARD: Settings & CRM ---
    path('dashboard/leads/delete/<int:pk>/', views.delete_lead, name='delete_lead'),
    path('dashboard/settings/', views.account_settings, name='account_settings'),
    path('dashboard/services/', views.manage_services, name='manage_services'),
    path('dashboard/services/add/', views.add_service, name='add_service'),
    path('dashboard/services/delete/<int:pk>/', views.delete_service, name='delete_service'),
    path('dashboard/article/delete/<int:pk>/', views.delete_article, name='delete_article'),

    # --- AGENCY HUB ---
    path('dashboard/agency/', views.manage_agency_site, name='manage_agency_site'),
    path('dashboard/agency/<int:agency_pk>/image/add/', views.add_agency_image, name='add_agency_image'),
    path('dashboard/agency/image/delete/<int:pk>/', views.delete_agency_image, name='delete_agency_image'),
    path('dashboard/agency/<int:agency_pk>/review/add/', views.add_agency_review, name='add_agency_review'),
    path('dashboard/agency/review/delete/<int:pk>/', views.delete_agency_review, name='delete_agency_review'),

    # --- AUDIENCE & BROADCASTS ---
    path('dashboard/audience/', views.manage_subscribers, name='manage_subscribers'),
    path('dashboard/audience/import-preview/', views.preview_import, name='preview_import'),
    path('dashboard/audience/subscriber/<int:pk>/edit/', views.edit_subscriber, name='edit_subscriber'),
    path('dashboard/audience/subscriber/<int:pk>/delete/', views.delete_subscriber, name='delete_subscriber'),
    path('dashboard/audience/mass-update-freq/', views.mass_update_review_freq, name='mass_update_review_freq'),
    path('dashboard/audience/export/', views.secure_export_subscribers, name='export_subscribers'),
    
    path('dashboard/broadcasts/', views.newsletter_dashboard, name='newsletter_dashboard'),
    path('dashboard/broadcasts/compose/', views.compose_newsletter, name='compose_newsletter'),
    path('dashboard/broadcasts/send/<int:pk>/', views.send_newsletter, name='send_newsletter'),

    # --- CRM: CARDS & REMINDERS ---
    path('dashboard/crm/', views.manage_cards, name='manage_cards'),
    path('dashboard/crm/card/<int:pk>/edit/', views.edit_card, name='edit_card'),
    path('dashboard/crm/card/<int:pk>/delete/', views.delete_card, name='delete_card'),
    path('dashboard/crm/upcoming/', views.upcoming_events, name='upcoming_events'),
    path('dashboard/crm/review-reminder/<int:pk>/send/', views.send_review_reminder, name='send_review_reminder'),
    path('dashboard/crm/review-reminders/bulk/', views.send_bulk_review_reminders, name='send_bulk_review_reminders'),

    # --- MISC ROUTES ---
    path('logout/', views.logout_view, name='logout'),
    path('agent/<slug:slug>/testimonials/', views.agent_testimonials, name='agent_testimonials'),
    path('agent/<slug:slug>/bio/', views.agent_bio, name='agent_bio'),
    path('agent/<slug:slug>/services/', views.agent_services, name='agent_services'),
    path('agent/<slug:slug>/review/<int:pk>/', views.single_testimonial, name='single_testimonial'),
    path('agent/<slug:slug>/vcard/', views.download_vcard, name='download_vcard'),
    path('review/submit/<str:token>/', views.client_review_submission, name='submit_review'),
    path('unsubscribe/<uuid:token>/', views.unsubscribe_client, name='unsubscribe'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]