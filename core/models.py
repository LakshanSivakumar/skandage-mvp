import uuid
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import string
import random
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from datetime import timedelta
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

    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, help_text="Used for instant lead notifications")
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
    # Add this to your Agent model
    is_bespoke = models.BooleanField(default=False, help_text="True if client paid for a 1-of-1 custom design")
    bespoke_template_name = models.CharField(max_length=50, blank=True, help_text="e.g., 'themes/karna_custom.html'")
    bespoke_data = models.JSONField(default=dict, blank=True, help_text="Stores unique editable fields just for this agent")
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
    video = models.FileField(upload_to='reviews/videos/', blank=True, null=True, help_text="Upload MP4 or MOV files")
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
    archived_at = models.DateTimeField(null=True, blank=True, help_text="When the agent soft-deleted this record")
    is_anonymized = models.BooleanField(default=False, help_text="True if PII was scrubbed after 7 years")
    is_subscribed = models.BooleanField(default=True, help_text="False if client opted out of bulk marketing/cards")
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, unique=True)    # --- ANONYMIZED DATABASE INDEXES (For SQL Queries) ---
    is_active = models.BooleanField(default=True)
    birth_month = models.IntegerField(null=True, blank=True, help_text="Used for safe SQL birthday querying")
    birth_day = models.IntegerField(null=True, blank=True, help_text="Used for safe SQL birthday querying")
    email_hash = models.CharField(max_length=64)
    name_hash = models.CharField(max_length=64, blank=True) # For exact duplicate hunting
    
    # --- ZERO-KNOWLEDGE ENCRYPTED PAYLOADS ---
    pipeline_status = models.CharField(max_length=20, choices=[('prospect', 'Prospect'), ('client', 'Client')], default='client')
    lead_source = models.CharField(max_length=20, choices=[('referred', 'Referred'), ('cold', 'Cold'), ('others', 'Others')], default='others')
    next_review_date = models.DateField(null=True, blank=True, help_text="Calculated date for the next policy review")
    review_freq_months = models.PositiveIntegerField(null=True, blank=True, help_text="Review interval in months (e.g. 6 or 12)")
    last_review_date = models.DateField(null=True, blank=True, help_text="Date of the most recent review — used to recalculate next review date")

    # --- ZERO-KNOWLEDGE ENCRYPTED PAYLOADS ---
    encrypted_name = models.BinaryField()
    encrypted_email = models.BinaryField()
    encrypted_dob = models.BinaryField(null=True, blank=True)
    encrypted_race = models.BinaryField()
    encrypted_gender = models.BinaryField()
    encrypted_tags = models.BinaryField(null=True, blank=True)
    
    # --- NEW: ENCRYPTED HQ FIELDS ---
    # Using default=b'' ensures your database migration won't crash!
    encrypted_phone = models.BinaryField(default=b'')
    encrypted_address = models.BinaryField(default=b'')
    encrypted_notes = models.BinaryField(default=b'')
    
    source = models.CharField(max_length=100, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('agent', 'email_hash')

    # ==========================================
    # SECURE PROPERTIES (Transparent Decryption)
    # ==========================================
    def _decrypt_field(self, field_data):
        if not field_data: return ""
        try:
            # PostgreSQL BinaryField returns memoryview objects, not bytes.
            # fernet.decrypt() requires bytes — convert before decrypting.
            if isinstance(field_data, memoryview):
                field_data = bytes(field_data)
            return fernet.decrypt(field_data).decode()
        except Exception: return ""

    def _encrypt_field(self, string_val):
        if not string_val: return b''
        return fernet.encrypt(str(string_val).encode())
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remember the original race when the object is loaded from the database
        self._original_race = self.race if self.pk else None
    # --- NAME ---
    @property
    def name(self):
        return self._decrypt_field(self.encrypted_name)

    @name.setter
    def name(self, value):
        val = value.strip() if value else ""
        self.encrypted_name = self._encrypt_field(val)
        self.name_hash = hashlib.sha256(val.lower().encode()).hexdigest() if val else ""

    # --- EMAIL ---
    @property
    def email(self):
        return self._decrypt_field(self.encrypted_email)
    @property
    def phone(self): return self._decrypt_field(self.encrypted_phone)
    @phone.setter
    def phone(self, value): self.encrypted_phone = self._encrypt_field(value)

    @property
    def address(self): return self._decrypt_field(self.encrypted_address)
    @address.setter
    def address(self, value): self.encrypted_address = self._encrypt_field(value)

    @property
    def notes(self): return self._decrypt_field(self.encrypted_notes)
    @notes.setter
    def notes(self, value): self.encrypted_notes = self._encrypt_field(value)
    
    @email.setter
    def email(self, value):
        if value:
            clean_email = value.strip().lower()
            self.email_hash = hash_email(clean_email)
            self.encrypted_email = self._encrypt_field(clean_email)
        else:
            self.email_hash = f"empty_{uuid.uuid4().hex}"
            self.encrypted_email = b''

    # --- DATE OF BIRTH ---
    @property
    def date_of_birth(self):
        raw_date = self._decrypt_field(self.encrypted_dob)
        if raw_date:
            try: return datetime.strptime(raw_date, '%Y-%m-%d').date()
            except ValueError: return None
        return None

    @date_of_birth.setter
    def date_of_birth(self, value):
        if not value:
            # Default to 1 Jan 2000 when no DOB is provided
            value = datetime(2000, 1, 1).date()
        # Store full date encrypted
        self.encrypted_dob = self._encrypt_field(value.strftime('%Y-%m-%d'))
        # Store harmless metadata for the SQL cron job
        self.birth_month = value.month
        self.birth_day = value.day

    # --- RACE, GENDER, TAGS ---
    @property
    def race(self): return self._decrypt_field(self.encrypted_race) or 'O'
    @race.setter
    def race(self, value): self.encrypted_race = self._encrypt_field(value)

    @property
    def gender(self): return self._decrypt_field(self.encrypted_gender) or 'U'
    @gender.setter
    def gender(self, value): self.encrypted_gender = self._encrypt_field(value)

    @property
    def tags(self): return self._decrypt_field(self.encrypted_tags)
    @tags.setter
    def tags(self, value): self.encrypted_tags = self._encrypt_field(value)

    @property
    def tag_list(self):
        tags_str = self.tags
        if not tags_str: return []
        return [t.strip() for t in tags_str.split(',') if t.strip()]

    # --- DISPLAY HELPERS ---
    def get_race_display(self):
        mapping = {'C': 'Chinese', 'M': 'Malay', 'I': 'Indian', 'O': 'Others'}
        return mapping.get(self.race, 'Others')

    def get_gender_display(self):
        mapping = {'M': 'Male', 'F': 'Female', 'U': 'Unspecified'}
        return mapping.get(self.gender, 'Unspecified')

    @property
    def age(self):
        dob = self.date_of_birth
        if not dob: return None
        today = datetime.today().date()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def save(self, *args, **kwargs):
        current_tags = self.tag_list
        race_tags_map = {
            'C': ['Lunar New Year', 'Mid-Autumn Festival'],
            'M': ['Hari Raya Aidilfitri', 'Hari Raya Haji'],
            'I': ['Deepavali', 'Pongal']
        }

        # --- SCENARIO A: BRAND NEW CLIENT ---
        if not self.pk:
            # 1. Add Universal Tags
            for fest in ['Christmas', 'New Year']:
                if fest not in current_tags:
                    current_tags.append(fest)
            
            # 2. Add Initial Race Tags
            if self.race in race_tags_map:
                for fest in race_tags_map[self.race]:
                    if fest not in current_tags:
                        current_tags.append(fest)

        # --- SCENARIO B: EXISTING CLIENT (RACE CHANGED) ---
        elif hasattr(self, '_original_race') and self._original_race != self.race:
            # 1. Strip out the specific tags from their old race
            old_tags = race_tags_map.get(self._original_race, [])
            current_tags = [t for t in current_tags if t not in old_tags]
            
            # 2. Inject the specific tags for their new race
            new_tags = race_tags_map.get(self.race, [])
            for fest in new_tags:
                if fest not in current_tags:
                    current_tags.append(fest)

        # Repackage the tags into the encrypted string
        self.tags = ", ".join(current_tags)
        
        # Update the original race tracker so subsequent saves in the same session work
        self._original_race = self.race

        # --- ENCRYPTION SAFETY FALLBACK ---
        if not getattr(self, 'email_hash', ''):
            self.email_hash = f"empty_{uuid.uuid4().hex}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or "Unknown Encrypted Client"
    

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
        # REMOVED 'subscriber__name' because the name is now fully encrypted
        ordering = ['-scheduled_date']

    def __str__(self):
        return f"{self.occasion} for {self.subscriber.name} ({self.status})"
    
class PendingAgentOnboarding(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved & Account Created'),
        ('rejected', 'Rejected')
    ]
    
    # 1. Basic Info
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, help_text="Mobile / WhatsApp Number")
    
    # 2. Professional Details
    agency_name = models.CharField(max_length=100, default="AIAFA", help_text="Which agency are they joining under?")
    job_title = models.CharField(max_length=100, default="Financial Consultant")
    requested_subdomain = models.CharField(max_length=100, help_text="e.g. 'benedict' for benedict.skandage.com")
    bio = models.TextField(blank=True, help_text="Agent's background story")
    headshot = models.ImageField(upload_to='onboarding/headshots/', blank=True, null=True)
    credentials_upload = models.FileField(upload_to='onboarding/credentials/', blank=True, null=True, help_text="PDF or Image of certifications")
    
    # 3. Migration & Socials
    existing_website = models.URLField(blank=True, null=True, help_text="Link to scrape existing testimonials from")
    linkedin = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    
    # 4. System Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.agency_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Check if this is an existing record being updated to 'approved'
        if self.pk:
            old_instance = PendingAgentOnboarding.objects.get(pk=self.pk)
            if old_instance.status != 'approved' and self.status == 'approved':
                self._automate_account_creation()
        
        super().save(*args, **kwargs)

    

class Feedback(models.Model):
    FEEDBACK_TYPES = [
        ('Bug Report', 'Bug Report'),
        ('Feature Request', 'Feature Request'),
        ('General Feedback', 'General Feedback'),
    ]
    STATUS_CHOICES = [
        ('New', 'New'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField()
    agency_name = models.CharField(max_length=100, blank=True)
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES, default='General Feedback')
    message = models.TextField(help_text="What is the #1 point of friction?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.feedback_type} from {self.name} - {self.status}"
    
class EmailOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_otp')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        # Generates a random 6-digit number
        self.otp = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.save()

    def is_valid(self):
        # OTP expires after 10 minutes
        return self.created_at >= timezone.now() - timedelta(minutes=10)
    
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('VAULT_VIEWED', 'Viewed Entire Vault'),
        ('CLIENT_VIEWED', 'Viewed Single Client Details'),
        ('CLIENT_EXPORTED', 'Exported Vault to CSV'),
        ('CLIENT_DELETED', 'Deleted Client Record'),
    ]
    
    agent = models.ForeignKey('Agent', on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_info = models.CharField(max_length=255, help_text="e.g., 'Client: John Doe (ID: 4)' or 'Exported 150 clients'")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.agent.name} - {self.action} at {self.timestamp}"