from django.urls import path, include
from . import views

urlpatterns = [
    # --- PUBLIC DOMAIN ROUTER ---
    path('', views.domain_router, name='home'),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # --- PUBLIC AGENT PAGES ---
    path('agent/<slug:slug>/', views.agent_profile, name='agent_profile'),
    path('read/<slug:slug>/', views.article_detail, name='article_detail'),

    # --- DASHBOARD (Protected) ---
    path('dashboard/', views.dashboard_stats, name='dashboard'), 
    path('dashboard/profile/', views.manage_profile, name='manage_profile'),
    path('dashboard/articles/', views.manage_articles, name='manage_articles'),
    path('dashboard/testimonials/', views.manage_testimonials, name='manage_testimonials'),

    # --- ACTIONS: Articles ---
    path('dashboard/article/new/', views.create_article, name='create_article'),
    path('dashboard/article/edit/<int:pk>/', views.edit_article, name='edit_article'),
    
    # --- ACTIONS: Credentials ---
    path('dashboard/credential/add/', views.add_credential, name='add_credential'),
    path('dashboard/credential/delete/<int:pk>/', views.delete_credential, name='delete_credential'),

    # --- ACTIONS: Testimonials ---
    path('dashboard/testimonial/add/', views.add_testimonial, name='add_testimonial'),     
    path('dashboard/testimonial/delete/<int:pk>/', views.delete_testimonial, name='delete_testimonial'), 
    path('dashboard/testimonial/edit/<int:pk>/', views.edit_testimonial, name='edit_testimonial'), 

    path('dashboard/leads/delete/<int:pk>/', views.delete_lead, name='delete_lead'),
    path('dashboard/settings/', views.account_settings, name='account_settings'),
    path('logout/', views.logout_view, name='logout'),
    path('agent/<slug:slug>/testimonials/', views.agent_testimonials, name='agent_testimonials'),
    path('agent/<slug:slug>/bio/', views.agent_bio, name='agent_bio'),
    path('agent/<slug:slug>/review/<int:pk>/', views.single_testimonial, name='single_testimonial'),
    path('agent/<slug:slug>/vcard/', views.download_vcard, name='download_vcard'),
    path('dashboard/services/', views.manage_services, name='manage_services'),
    path('dashboard/services/add/', views.add_service, name='add_service'),
    path('dashboard/services/delete/<int:pk>/', views.delete_service, name='delete_service'),
    path('dashboard/article/delete/<int:pk>/', views.delete_article, name='delete_article'),

    # NEW: Credential Actions
    path('dashboard/credential/edit/<int:pk>/', views.edit_credential, name='edit_credential'),

    # NEW: Testimonial Feature Toggle
    path('dashboard/testimonial/toggle-feature/<int:pk>/', views.toggle_testimonial_feature, name='toggle_testimonial_feature'),
    path('dashboard/credentials/reorder/', views.reorder_credentials, name='reorder_credentials'),
    path('dashboard/testimonials/import/', views.import_testimonials, name='import_testimonials'),
    path('dashboard/testimonials/generate-link/', views.generate_review_link, name='generate_review_link'),
    path('review/submit/<str:token>/', views.client_review_submission, name='submit_review'),
    path('dashboard/agency/', views.manage_agency_site, name='manage_agency_site'),
    path('dashboard/agency/<int:agency_pk>/image/add/', views.add_agency_image, name='add_agency_image'),
    path('dashboard/agency/image/delete/<int:pk>/', views.delete_agency_image, name='delete_agency_image'),
    path('dashboard/agency/<int:agency_pk>/review/add/', views.add_agency_review, name='add_agency_review'),
    path('dashboard/agency/review/delete/<int:pk>/', views.delete_agency_review, name='delete_agency_review'),

]