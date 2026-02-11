from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
import uuid

class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, help_text="This will be the URL: skandage.com/agent/ryan-siow")
    title = models.CharField(max_length=100, default="Financial Consultant")
    company = models.CharField(max_length=100, default="Great Eastern")
    tagline = models.CharField(max_length=200, default="Here for you, always.")
    profile_views = models.PositiveIntegerField(default=0)
    # WhatsApp Feature
    phone_number = models.CharField(max_length=20, help_text="Format: 6591234567 (No + sign)")
    whatsapp_message = models.CharField(max_length=200, default="Hi, I saw your profile and would like to know more.")
    linkedin = models.URLField(blank=True, help_text="Full URL (e.g. https://linkedin.com/in/name)")
    instagram = models.URLField(blank=True, help_text="Full URL (e.g. https://instagram.com/name)")
    facebook = models.URLField(blank=True, help_text="Full URL (e.g. https://facebook.com/name)")
    disclaimer = models.TextField(
        default="The content on this website is strictly for information and educational purposes only and does not constitute financial advice. Investments are subject to market risks. Please consult a qualified financial consultant before making any decisions. Views expressed here are my own and do not necessarily reflect the official policy or position of my company.\n\nThis advertisement has not been reviewed by the Monetary Authority of Singapore.",
        help_text="This text appears in the footer of every page."
    )
    
    # Profile Details
    headshot = models.ImageField(upload_to='headshots/', blank=True, null=True)
    bio = models.TextField(blank=True)

    # --- THEMES & LAYOUTS ---
    THEME_CHOICES = [
        ('luxe', 'Luxe Minimal (Stone & Amber)'),
        ('corporate', 'Corporate Blue (Navy & White)'),
        ('midnight', 'Midnight Neon (Dark & Cyan)'),
        ('sunset', 'Sunset (Warm Orange & Cream)'),
        ('cotton', 'Cotton (Monochrome Black & White)'),
        ('glacier', 'Glacier (White & Icy Blue)'),
        ('blush', 'Blush (White & Rose Gold)'),
    ]
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='luxe')

    LAYOUT_CHOICES = [
        ('classic', 'Classic Split (Image Left, Text Right)'),
        ('centered', 'Impact Center (Centered Text & Image)'),
        ('minimal', 'Minimalist (Text Only, No Hero Image)'),
    ]
    layout = models.CharField(max_length=20, choices=LAYOUT_CHOICES, default='classic')

    can_upload_testimonials = models.BooleanField(
        default=False, 
        help_text="If True, agent can add/upload testimonials freely. If False, button is hidden."
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Agent.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def whatsapp_link(self):
        from urllib.parse import quote
        text = quote(self.whatsapp_message)
        return f"https://wa.me/{self.phone_number}?text={text}"

    def __str__(self):
        return self.name

class Testimonial(models.Model):
    agent = models.ForeignKey(Agent, related_name='testimonials', on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True, help_text="e.g. 'Built on Trust' or 'Great Service'")
    client_name = models.CharField(max_length=100)
    review_text = models.TextField()
    screenshot = models.ImageField(upload_to='reviews/', blank=True, null=True, help_text="Upload WhatsApp screenshot if available")
    is_featured = models.BooleanField(default=False, help_text="Check this to pin this review to the homepage")
    is_published = models.BooleanField(default=True, help_text="If False, it will be hidden until approved.")
    submission_date = models.DateTimeField(auto_now_add=True, null=True) # To sort pending ones
    def __str__(self):
        status = "★" if self.is_featured else ""
        return f"{status} {self.client_name}"

class Service(models.Model):
    agent = models.ForeignKey(Agent, related_name='services', on_delete=models.CASCADE)
    title = models.CharField(max_length=100, help_text="e.g., Critical Illness Protection")
    description = models.TextField(blank=True)
    
    # NEW: Icon Picker
    ICON_CHOICES = [
        ('bxs-shield', 'Protection / Shield'),
        ('bxs-heart', 'Life / Health'),
        ('bxs-briefcase', 'Retirement / Business'),
        ('bxs-bar-chart-alt-2', 'Investment / Growth'),
        ('bxs-graduation', 'Education / Planning'),
        ('bxs-home-heart', 'Mortgage / Housing'),
        ('bxs-plane-alt', 'Travel / Lifestyle'),
        ('bxs-badge-dollar', 'Wealth / Tax'),
    ]
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, default='bxs-shield')
    
    def __str__(self):
        return self.title

class Credential(models.Model):
    agent = models.ForeignKey(Agent, related_name='credentials', on_delete=models.CASCADE)
    title = models.CharField(max_length=100, help_text="e.g. MDRT 2024, ChFC, Top Rookie")
    issuer = models.CharField(max_length=100, help_text="e.g. Million Dollar Round Table, Prudential")
    year = models.CharField(max_length=20, blank=True, help_text="Optional, e.g. 2023")
    order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['order']
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
    
class Article(models.Model):
    agent = models.ForeignKey(Agent, related_name='articles', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True) 
    cover_image = models.ImageField(upload_to='article_headers/', blank=True, null=True)
    content = models.TextField(help_text="Write your article here.")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{self.agent.id}" 
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
class ReviewLink(models.Model):
    token = models.CharField(max_length=12, unique=True, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            # Generate a short 8-character ID (e.g., "a1b2c3d4")
            self.token = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)