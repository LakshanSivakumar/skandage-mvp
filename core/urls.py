from django.urls import path
from . import views
from django.urls import include
urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'), 
    path('accounts/', include('django.contrib.auth.urls')), 
    path('agent/<slug:slug>/', views.agent_profile, name='agent_profile'),
    path('dashboard/testimonial/add/', views.add_testimonial, name='add_testimonial'),     
    path('dashboard/testimonial/delete/<int:pk>/', views.delete_testimonial, name='delete_testimonial'), 
    path('dashboard/testimonial/edit/<int:pk>/', views.edit_testimonial, name='edit_testimonial'), # <--- New
    path('dashboard/bio/', views.edit_bio, name='edit_bio'),             # <--- New
    path('dashboard/headshot/', views.upload_headshot, name='upload_headshot'), # <--- New
]