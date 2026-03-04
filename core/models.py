import uuid
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)
class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True, help_text="This will be the URL: skandage.com/agent/ryan-siow")
    title = models.CharField(max_length=100, default="Financial Consultant")
    company = models.CharField(max_length=100, default="Great Eastern")
    tagline = models.CharField(max_length=200, default="Here for you, always.")
    vcard_downloads = models.PositiveIntegerField(default=0) # <--- NEW FIELD
    profile_views = models.PositiveIntegerField(default=0)
    calendly_link = models.URLField(max_length=255, blank=True, null=True, help_text="e.g., https://calendly.com/your-username")
    # WhatsApp Feature
    phone_number = models.CharField(max_length=20, help_text="Format: 6591234567 (No + sign)")
    whatsapp_message = models.CharField(max_length=200, default="Hi, I saw your profile and would like to know more.")
    linkedin = models.URLField(blank=True, help_text="Full URL")
    instagram = models.URLField(blank=True, help_text="Full URL")
    facebook = models.URLField(blank=True, help_text="Full URL")
    disclaimer = models.TextField(
        default="The content on this website is strictly for information and educational purposes only and does not constitute financial advice. Investments are subject to market risks. Please consult a qualified financial consultant before making any decisions. Views expressed here are my own and do not necessarily reflect the official policy or position of my company.\n\nThis advertisement has not been reviewed by the Monetary Authority of Singapore.",
        help_text="This text appears in the footer of every page."
    )
    automation_mode = models.CharField(max_length=10, choices=[('manual', 'Manual Approval'), ('auto', 'Fully Automated')], default='manual')
    notification_email = models.EmailField(blank=True, null=True, help_text="Optional: Receive daily summaries here instead of your login email.")
    # Profile Details
    headshot = models.ImageField(upload_to='headshots/', blank=True, null=True)
    bio = models.TextField(blank=True)

    # --- THEMES & LAYOUTS ---
    # In core/models.py

    THEME_CHOICES = [
        ('luxe', 'Luxe Minimal (Stone & Amber)'),
        ('corporate', 'Corporate Blue (Navy & White)'),
        ('midnight', 'Midnight Neon (Dark & Cyan)'),
        ('midnight_rose', 'Midnight Rose (Black & Pink)'),
        ('executive', 'Executive Gold (Black & Gold)'),
        ('vogue', 'Vogue Editorial (Alabaster & Charcoal)'), # NEW
        ('sterling', 'Sterling Fintech (Slate & Blue)'),
        ('emerald', 'Private Client (Deep Green)'),
        ('obsidian', 'Obsidian (Black & White)'),
        ('royal', 'Royal Navy (Deep Blue & Silver)'),
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
        help_text="If True, agent can add/upload testimonials freely."
    )

    # --- NEW FIELDS ---
    is_public = models.BooleanField(
        default=True,
        help_text="Uncheck this to disable the profile (404 error)."
    )
    custom_domain = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="e.g. 'yq-partners.com'. If set, agent loads on this domain."
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
    title = models.CharField(max_length=200, blank=True)
    client_name = models.CharField(max_length=100)
    review_text = models.TextField()
    screenshot = models.ImageField(upload_to='reviews/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    submission_date = models.DateTimeField(auto_now_add=True, null=True)
    def __str__(self):
        return f"{self.client_name}"

class Service(models.Model):
    agent = models.ForeignKey(Agent, related_name='services', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
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
    def __str__(self): return self.title

class Credential(models.Model):
    agent = models.ForeignKey(Agent, related_name='credentials', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    issuer = models.CharField(max_length=100)
    year = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['order']
    def __str__(self): return self.title
    
class Lead(models.Model):
    agent = models.ForeignKey(Agent, related_name='leads', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Lead from {self.name}"
    
class Article(models.Model):
    agent = models.ForeignKey(Agent, related_name='articles', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True) 
    cover_image = models.ImageField(upload_to='article_headers/', blank=True, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            self.slug = f"{base_slug}-{self.agent.id}" 
        super().save(*args, **kwargs)
    def __str__(self): return self.title
    
class ReviewLink(models.Model):
    token = models.CharField(max_length=12, unique=True, editable=False)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    client_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)

class Agency(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agency_site', null=True, blank=True)
    name = models.CharField(max_length=100, default="YQ Partners")
    domain = models.CharField(max_length=100, unique=True, help_text="e.g. yq-partners.com")
    page_views = models.PositiveIntegerField(default=0)
    # Branding
    logo = models.ImageField(upload_to='agency/logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#2563EB", help_text="Hex code (e.g. #2563EB)")
    secondary_color = models.CharField(max_length=7, default="#1E293B", help_text="Hex code (e.g. #1E293B)")
    
    # Content: Hero
    hero_headline = models.CharField(max_length=200, default="Securing Futures, Building Legacies.")
    hero_subheadline = models.TextField(default="A collective of top-tier financial consultants dedicated to providing comprehensive wealth management.")
    hero_image = models.ImageField(upload_to='agency/hero/', blank=True, null=True)
    
    # Content: About & Values (NEW)
    about_text = models.TextField(blank=True, default="We are a premier agency focused on...")
    values_text = models.TextField(blank=True, default="Integrity, Excellence, Compassion.")

    # Contact Info
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.domain

class AgencyImage(models.Model):
    agency = models.ForeignKey(Agency, related_name='gallery_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='agency/gallery/')
    caption = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AgencyReview(models.Model):
    agency = models.ForeignKey(Agency, related_name='fc_reviews', on_delete=models.CASCADE)
    fc_name = models.CharField(max_length=100)
    fc_role = models.CharField(max_length=100, default="Financial Consultant")
    fc_photo = models.ImageField(upload_to='agency/fc_reviews/', blank=True, null=True)
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Newsletter(models.Model):
    agent = models.ForeignKey(Agent, related_name='newsletters', on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    content = models.TextField(help_text="HTML content of the newsletter")
    attachment = models.FileField(upload_to='newsletters/attachments/', blank=True, null=True, help_text="Optional PDF attachment")
    html_file = models.FileField(upload_to='newsletters/html/', blank=True, null=True, help_text="Upload a custom HTML template")
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('sent', 'Sent')], default='draft')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.subject
    
def hash_email(email):
    return hashlib.sha256(email.lower().strip().encode('utf-8')).hexdigest()

class Subscriber(models.Model):
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE, related_name='subscribers')
    name = models.CharField(max_length=255)
    
    # --- THE RESTORED DATABASE FIELD ---
    is_active = models.BooleanField(default=True)
    
    # --- DEMOGRAPHIC FIELDS FOR CARD ENGINE ---
    RACE_CHOICES = [
        ('C', 'Chinese'), 
        ('M', 'Malay'), 
        ('I', 'Indian'), 
        ('O', 'Others')
    ]
    GENDER_CHOICES = [
        ('M', 'Male'), 
        ('F', 'Female'), 
        ('U', 'Unspecified')
    ]
    
    date_of_birth = models.DateField(null=True, blank=True)
    race = models.CharField(max_length=1, choices=RACE_CHOICES, default='O')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    
    # --- PDPA SECURE ENCRYPTED FIELDS ---
    email_hash = models.CharField(max_length=64)
    encrypted_email = models.BinaryField()
    source = models.CharField(max_length=100, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This is the constraint that was crashing earlier. 
        # The uuid logic below prevents it from crashing on empty emails.
        unique_together = ('agent', 'email_hash')

    @property
    def email(self):
        if not self.encrypted_email:
            return ""
        try:
            token = self.encrypted_email
            # Django BinaryField returns memoryview — convert to bytes
            if isinstance(token, memoryview):
                token = token.tobytes()
            elif isinstance(token, str):
                token = token.encode('utf-8')
            if not token:
                return ""
            decrypted = fernet.decrypt(token).decode('utf-8')
            # Hide placeholder emails from display
            if decrypted.endswith('@placeholder.internal'):
                return ""
            return decrypted
        except Exception:
            return ""

    @email.setter
    def email(self, value):
        if value:
            self._email_decrypted = value.strip().lower()
            self.email_hash = hash_email(self._email_decrypted)
            self.encrypted_email = fernet.encrypt(self._email_decrypted.encode())
        else:
            self._email_decrypted = ""
            # Generate a unique placeholder so empty emails don't collide
            self.email_hash = f"empty_{uuid.uuid4().hex}"
            self.encrypted_email = b''

    def save(self, *args, **kwargs):
        # Final safety check before database commit to prevent IntegrityErrors
        current_email = getattr(self, '_email_decrypted', '')
        
        if not current_email:
            if not self.email_hash or not self.email_hash.startswith('empty_'):
                self.email_hash = f"empty_{uuid.uuid4().hex}"
            self.encrypted_email = b''
        else:
            self.email_hash = hash_email(current_email)
            self.encrypted_email = fernet.encrypt(current_email.encode())

        super().save(*args, **kwargs)

    @property
    def age(self):
        """Calculate age from date_of_birth. Returns None if DOB not set."""
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def auto_tags(self):
        """Auto-generate festival tags based on race (CMIO)."""
        tags = []
        race_tags = {
            'C': ['Lunar New Year', 'Mid-Autumn Festival'],
            'M': ['Hari Raya Aidilfitri', 'Hari Raya Haji'],
            'I': ['Deepavali', 'Pongal', 'Thaipusam'],
        }
        if self.race in race_tags:
            tags.extend(race_tags[self.race])
        tags.extend(['Christmas', 'New Year'])
        return tags

    def __str__(self):
        return self.name

class CardTemplate(models.Model):
    """
    Phase 3: Asset Matrix — each card design has targeting rules.
    The system picks a matching template based on demographics.
    """
    GENDER_TARGET_CHOICES = [
        ('M', 'Males Only'),
        ('F', 'Females Only'),
        ('A', 'Any Gender'),
    ]

    OCCASION_CHOICES = [
        ('Birthday', 'Birthday'),
        ('Lunar New Year', 'Lunar New Year'),
        ('Mid-Autumn Festival', 'Mid-Autumn Festival'),
        ('Deepavali', 'Deepavali'),
        ('Hari Raya Aidilfitri', 'Hari Raya Aidilfitri'),
        ('Hari Raya Haji', 'Hari Raya Haji'),
        ('Christmas', 'Christmas'),
        ('New Year', 'New Year'),
        ('Pongal', 'Pongal'),
        ('Other', 'Other'),
    ]

    # Each agent manages their own card library
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE, related_name='card_templates', null=True, blank=True)

    name = models.CharField(max_length=100, help_text="Internal name (e.g., 'Professional Navy Blue')")
    image = models.ImageField(upload_to='card_templates/', blank=True, null=True, help_text="The card design image (optional)")
    occasion = models.CharField(max_length=100, choices=OCCASION_CHOICES, help_text="e.g., 'Lunar New Year', 'Deepavali', 'Birthday', 'Christmas'")
    default_message = models.TextField(
        default="Wishing you joy and happiness on this special occasion!",
        help_text="Default message sent with this card design"
    )

    # Targeting rules
    target_gender = models.CharField(max_length=1, choices=GENDER_TARGET_CHOICES, default='A')
    target_age_min = models.PositiveIntegerField(default=0, help_text="Minimum age (inclusive)")
    target_age_max = models.PositiveIntegerField(default=120, help_text="Maximum age (inclusive)")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['occasion', 'name']

    def matches_subscriber(self, subscriber):
        """Check if this card template matches a subscriber's demographics."""
        # Gender check
        if self.target_gender != 'A':
            if subscriber.gender != self.target_gender:
                return False
        # Age check
        age = subscriber.age
        if age is not None:
            if age < self.target_age_min or age > self.target_age_max:
                return False
        return True

    def __str__(self):
        return f"{self.name} ({self.occasion}) — {self.get_target_gender_display()}, Ages {self.target_age_min}-{self.target_age_max}"


class GlobalNewsletter(models.Model):
    title = models.CharField(max_length=200, help_text="Internal title (e.g., 'March 2026 Update')")
    subject = models.CharField(max_length=200, help_text="The exact email subject line clients will see")
    content = models.TextField(help_text="Paste your plain text or paragraph content here. Do not add HTML, the wrapper handles that.")
    
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {'SENT' if self.is_sent else 'DRAFT'}"
    
class CardLog(models.Model):
    """
    Tracks every card generated, whether sent, pending, or failed.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='card_logs')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='card_logs')
    card_template = models.ForeignKey(CardTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    occasion = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    scheduled_date = models.DateField(help_text="The actual date of the birthday/festival")
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('subscriber', 'occasion', 'scheduled_date')
        ordering = ['-scheduled_date', 'subscriber__name']

    def __str__(self):
        return f"{self.occasion} for {self.subscriber.name} ({self.status})"