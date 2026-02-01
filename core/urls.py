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

]