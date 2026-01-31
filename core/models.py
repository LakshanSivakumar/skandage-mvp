from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) # <--- Add this line
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, help_text="This will be the URL: skandage.com/agent/ryan-siow")
    title = models.CharField(max_length=100, default="Financial Consultant")
    company = models.CharField(max_length=100, default="Great Eastern")
    tagline = models.CharField(max_length=200, default="Here for you, always.")
    # The "Killer" Feature (WhatsApp)
    phone_number = models.CharField(max_length=20, help_text="Format: 6591234567 (No + sign)")
    whatsapp_message = models.CharField(max_length=200, default="Hi, I saw your profile and would like to know more.")
    
    # Profile Details
    headshot = models.ImageField(upload_to='headshots/', blank=True, null=True)
    bio = models.TextField(blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def whatsapp_link(self):
        # Auto-generates the wa.me link with pre-filled text
        from urllib.parse import quote
        text = quote(self.whatsapp_message)
        return f"https://wa.me/{self.phone_number}?text={text}"

    def __str__(self):
        return self.name

class Testimonial(models.Model):
    agent = models.ForeignKey(Agent, related_name='testimonials', on_delete=models.CASCADE)
    client_name = models.CharField(max_length=100)
    review_text = models.TextField()
    screenshot = models.ImageField(upload_to='reviews/', blank=True, null=True, help_text="Upload WhatsApp screenshot if available")
    
    def __str__(self):
        return f"Review for {self.agent.name} by {self.client_name}"

class Service(models.Model):
    agent = models.ForeignKey(Agent, related_name='services', on_delete=models.CASCADE)
    title = models.CharField(max_length=100, help_text="e.g., Critical Illness Protection")
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.title

class Credential(models.Model):
    agent = models.ForeignKey(Agent, related_name='credentials', on_delete=models.CASCADE)
    title = models.CharField(max_length=100, help_text="e.g. MDRT 2024, ChFC, Top Rookie")
    issuer = models.CharField(max_length=100, help_text="e.g. Million Dollar Round Table, Prudential")
    year = models.CharField(max_length=20, blank=True, help_text="Optional, e.g. 2023")
    
    def __str__(self):
        return self.title
    
class Lead(models.Model):
    agent = models.ForeignKey(Agent, related_name='leads', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead from {self.name}"