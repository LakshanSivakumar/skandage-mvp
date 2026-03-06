import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib import messages
from django.urls import reverse
from .models import Agent, Testimonial, Lead, Article, Credential, Service, ReviewLink, Agency, AgencyImage, AgencyReview, PendingAgentOnboarding
from .forms import AgentProfileForm, TestimonialForm, LeadForm, ArticleForm, CredentialForm, UserUpdateForm, ServiceForm, ClientSubmissionForm, AgencySiteForm, AgencyReviewForm, AgencyImageForm
from .themes import THEMES
from django.http import HttpResponse, JsonResponse
from django.db.models import F, Max
from .utils import scrape_and_save_testimonials
from django.core.signing import Signer, BadSignature
import csv
import io
from django.core.mail import send_mass_mail
from email.mime.application import MIMEApplication # <--- NEW IMPORT
from django.utils import timezone
from .models import Subscriber, Newsletter, CardTemplate
from django.core.mail import get_connection, EmailMultiAlternatives
from django.utils.html import strip_tags
from .models import hash_email
from django.template.loader import render_to_string
from .utils_import import smart_parse_clients
from datetime import datetime
from datetime import date
from django.db.models import Q
from .models import CardLog
from django.conf import settings
import hashlib
import requests
import calendar
from datetime import datetime, date
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User

def add_months_to_date(source_date_str, months):
    """Calculates future review dates based on frequency."""
    if not source_date_str or not months: return None
    try:
        # Standardize Excel/CSV date formats (e.g., 2026-03-04 or 04/03/2026)
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                sourcedate = datetime.strptime(str(source_date_str).strip(), fmt).date()
                break
            except ValueError: continue
        else: return None

        month = sourcedate.month - 1 + int(float(months))
        year = sourcedate.year + month // 12
        month = month % 12 + 1
        day = min(sourcedate.day, calendar.monthrange(year, month)[1])
        return date(year, month, day).strftime('%Y-%m-%d')
    except Exception: return None
# ==========================
# VCARD DOWNLOAD VIEW
# ==========================
def download_vcard(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True)
    
    # --- NEW: Track the download ---
    agent.vcard_downloads = F('vcard_downloads') + 1
    agent.save(update_fields=['vcard_downloads'])
    # -------------------------------
    
    vcard_data = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{agent.name}",
        f"N:{agent.name};;;;",
        f"ORG:{agent.company}",
        f"TITLE:{agent.title}",
        f"TEL;TYPE=CELL:{agent.phone_number}",
        f"URL:{request.build_absolute_uri(f'/agent/{agent.slug}/')}",
    ]
    if agent.whatsapp_message:
        vcard_data.append(f"NOTE:WhatsApp: https://wa.me/{agent.phone_number}")
    vcard_data.append("END:VCARD")
    response = HttpResponse("\n".join(vcard_data), content_type="text/x-vcard")
    response["Content-Disposition"] = f'attachment; filename="{agent.slug}.vcf"'
    return response

# ==========================================
# PUBLIC ROUTER (The "Brain")
# ==========================================
def domain_router(request):
    host = request.get_host().split(':')[0].lower()
    subdomain = host.split('.')[0]

    if host.startswith('app.') or subdomain == 'app':
        return redirect('login') 
    if subdomain == 'onboarding':
        return onboarding_form_view(request)
    if host in ['skandage.com', 'www.skandage.com', 'localhost', '127.0.0.1']:
        return render(request, 'core/index.html', {'brand': 'skandage'})

    # --- AGENCY SITE LOGIC ---
    agency_site = Agency.objects.filter(domain__in=[host, f"www.{host}", host.replace('www.', '')]).first()
    
    if agency_site:
        Agency.objects.filter(pk=agency_site.pk).update(page_views=F('page_views') + 1)
        team_members = Agent.objects.filter(
            custom_domain__in=[agency_site.domain, host, host.replace('www.', '')], 
            is_public=True
        )
        
        # NEW: Fetch Gallery & Reviews
        gallery = agency_site.gallery_images.all().order_by('-created_at')
        fc_reviews = agency_site.fc_reviews.all().order_by('-created_at')

        return render(request, 'core/agency_landing.html', {
            'agency': agency_site,
            'team': team_members,
            'gallery': gallery,
            'fc_reviews': fc_reviews
        })

    return agent_profile(request, slug=subdomain)
@login_required
def manage_agency_site(request):
    try:
        agency = Agency.objects.get(owner=request.user)
    except Agency.DoesNotExist:
        agency = Agency.objects.create(owner=request.user, domain="yq-partners.com", name="YQ Partners")

    if request.method == 'POST' and 'update_settings' in request.POST:
        form = AgencySiteForm(request.POST, request.FILES, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated!")
            return redirect('manage_agency_site')
    else:
        form = AgencySiteForm(instance=agency)

    return render(request, 'core/manage_agency.html', {
        'form': form, 
        'agency': agency,
        'image_form': AgencyImageForm(),
        'review_form': AgencyReviewForm()
    })

@login_required
def add_agency_image(request, agency_pk):
    # Fetch the specific agency by ID, ensuring the user has permission (e.g. is owner)
    # Using owner=request.user ensures security so random people can't add photos to your agency
    agency = get_object_or_404(Agency, pk=agency_pk, owner=request.user)
    
    if request.method == 'POST':
        form = AgencyImageForm(request.POST, request.FILES)
        if form.is_valid():
            img = form.save(commit=False)
            # Explicitly link the new image to the fetched agency
            img.agency = agency
            img.save()
            messages.success(request, "Image added to gallery.")
        else:
            # Useful for debugging if forms fail silently
            print(form.errors)
            messages.error(request, "Error adding image. Please check the form.")
            
    return redirect('manage_agency_site')

@login_required
def delete_agency_image(request, pk):
    # Ensure the image belongs to an agency owned by the current user
    img = get_object_or_404(AgencyImage, pk=pk, agency__owner=request.user)
    img.delete()
    messages.success(request, "Image deleted.")
    return redirect('manage_agency_site')

@login_required
def add_agency_review(request, agency_pk):
    # Fetch specific agency by ID and ownership
    agency = get_object_or_404(Agency, pk=agency_pk, owner=request.user)
    
    if request.method == 'POST':
        form = AgencyReviewForm(request.POST, request.FILES)
        if form.is_valid():
            rev = form.save(commit=False)
            # Explicitly link the new review to the fetched agency
            rev.agency = agency
            rev.save()
            messages.success(request, "FC Review added.")
        else:
             print(form.errors)
             messages.error(request, "Error adding review.")

    return redirect('manage_agency_site')

@login_required
def delete_agency_review(request, pk):
    # Ensure review belongs to user's agency
    rev = get_object_or_404(AgencyReview, pk=pk, agency__owner=request.user)
    rev.delete()
    messages.success(request, "Review deleted.")
    return redirect('manage_agency_site')
def agent_profile(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True)
    
    host = request.get_host().lower()
    
    # Domain Restriction Check
    if 'skandage.com' not in host and 'localhost' not in host and '127.0.0.1' not in host:
        # If agent has NO custom domain set, or the current host doesn't match their allowed domain
        if not agent.custom_domain or (agent.custom_domain not in host):
            return render(request, 'core/error.html', {'message': 'This profile is not available on this domain.'})

    session_key = f'viewed_agent_{agent.pk}'
    if not request.session.get(session_key, False):
        agent.profile_views = F('profile_views') + 1
        agent.save(update_fields=['profile_views'])
        request.session[session_key] = True

    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    testimonials = agent.testimonials.filter(is_published=True).order_by('-is_featured', '-id')[:4]    
    services = agent.services.all()

    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.agent = agent
            lead.save()
            hashed = hash_email(lead.email)
            if not Subscriber.objects.filter(agent=agent, email_hash=hashed).exists():
                sub = Subscriber(agent=agent, name=lead.name, source='website_lead')
                sub.email = lead.email # Triggers the encryption setter!
                sub.save()

            telegram_msg = (
                f"🚨 <b>New Lead Alert!</b>\n\n"
                f"<b>Profile:</b> {agent.name}\n"
                f"<b>Name:</b> {lead.name}\n"
                f"<b>Email:</b> {lead.email}\n"
                f"<b>Phone:</b> {request.POST.get('phone', 'N/A')}\n\n"
                f"<i>Log in to Skandage to view details.</i>"
            )
            
            # Hardcode for testing, but later you can add 'telegram_chat_id' to your Agent model!
            BOT_TOKEN = "8761812137:AAE8fcj89fFeP2HJatxX9KBVfiZNXUohB3A"
            CHAT_ID = "1894504369" 
            
            send_telegram_notification(BOT_TOKEN, CHAT_ID, telegram_msg)
            # --- SEND NEW LEAD EMAIL NOTIFICATION TO AGENT ---
            try:
                email_context = {
                    'lead': lead,
                    'domain': request.get_host(),
                }
                html_body = render_to_string('core/emails/new_lead.html', email_context)
                text_body = strip_tags(html_body)

                notification = EmailMultiAlternatives(
                    subject=f"New Lead: {lead.name} just inquired on your profile!",
                    body=text_body,
                    from_email=f"Skandage <updates@skandage.com>",
                    to=[agent.user.email],
                )
                notification.attach_alternative(html_body, "text/html")
                notification.send()
            except Exception as e:
                print(f"Failed to send new lead notification: {e}")
            # ---------------------------
        is_calculator = request.POST.get('is_calculator')
        if is_calculator == 'true':
            client_name = request.POST.get('name', 'there').replace(' (Calculator Lead)', '')
            client_email = request.POST.get('email')
            
            context = {
                'agent': agent,
                'client_name': client_name,
                'income': request.POST.get('calc_income'),
                'dependents': request.POST.get('calc_dependents'),
                'liabilities': request.POST.get('calc_liabilities'),
                'existing': request.POST.get('calc_existing'),
                'recommended': request.POST.get('calc_recommended'),
                'gap': request.POST.get('calc_gap'),
                'request': request,
            }
            
            html_content = render_to_string('core/emails/coverage_report.html', context)
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(
                subject=f"Your Coverage Gap Analysis - {agent.name}",
                body=text_content,
                from_email=f"{agent.name} <reports@skandage.com>",
                to=[client_email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            try:
                msg.send()
            except Exception as e:
                print(f"Failed to send calc report: {e}")
        # -----------------------------------
        
        messages.success(request, "Your message has been sent successfully!")
        return redirect('agent_profile', slug=agent.slug)

    else:
        form = LeadForm()

    context = {
        'agent': agent,
        'testimonials': testimonials,
        'services': services,
        'articles': agent.articles.all().order_by('-created_at')[:3],
        'credentials': agent.credentials.all().order_by('order'),
        'total_testimonials': agent.testimonials.filter(is_published=True).count(),
        'theme': theme_config
    }

    # --- VIP ARCHITECTURE ROUTING ---
    if getattr(agent, 'is_bespoke', False) and getattr(agent, 'bespoke_template_name', ''):
        # Inject her custom JSON dictionary directly into the template context
        context['custom_fields'] = agent.bespoke_data or {}
        return render(request, agent.bespoke_template_name, context)
    else:
        # Load the standard Skandage template for everyone else
        return render(request, 'core/agent_profile.html', context)

def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, agent__is_public=True)
    return render(request, 'core/article_detail.html', {'article': article, 'agent': article.agent})

# ==========================================
# CLIENT REVIEW SUBMISSION
# ==========================================

@login_required
@require_POST
def generate_review_link(request):
    try:
        data = json.loads(request.body)
        client_name = data.get('client_name', '').strip()
        if not client_name:
            return JsonResponse({'status': 'error', 'message': 'Client name is required'}, status=400)
            
        link = ReviewLink.objects.create(
            agent=request.user.agent,
            client_name=client_name
        )
        path = reverse('submit_review', args=[link.token])
        full_url = request.build_absolute_uri(path)
        return JsonResponse({'status': 'success', 'url': full_url})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def client_review_submission(request, token):
    try:
        review_link = ReviewLink.objects.get(token=token)
    except ReviewLink.DoesNotExist:
        return render(request, 'core/error.html', {'message': 'Invalid link.'})
    
    if review_link.is_used:
         return render(request, 'core/error.html', {'message': 'This link has already been used.'})

    agent = review_link.agent
    
    if request.method == 'POST':
        form = ClientSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.agent = agent
            testimonial.client_name = review_link.client_name
            testimonial.is_published = False # Pending approval
            testimonial.save()
            
            review_link.is_used = True
            review_link.save()
            return render(request, 'core/review_thank_you.html', {'agent': agent})
    else:
        form = ClientSubmissionForm()

    return render(request, 'core/client_review_form.html', {
        'form': form, 
        'agent': agent, 
        'client_name': review_link.client_name
    })

# ==========================================
# DASHBOARD VIEWS
# ==========================================

@login_required
def dashboard_stats(request):
    agency = Agency.objects.filter(owner=request.user).first()
    
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        agent = None

    if agency and not agent:
        context = {
            'agency': agency,
            'is_agency_admin': True, 
            'section': 'stats'
        }
        return render(request, 'core/dashboard_stats.html', context)

    if not agent:
        agent = Agent.objects.create(user=request.user, name=request.user.username)

    leads = Lead.objects.filter(agent=agent).order_by('-created_at')
    
    # ==========================================
    # NEW: ADVANCED ANALYTICS CALCULATIONS
    # ==========================================
    audience_size = agent.subscribers.filter(is_active=True).count()
    broadcasts_sent = agent.newsletters.filter(status='sent').count()
    
    # Calculate Conversion Rate (%) safely to avoid ZeroDivisionError
    conversion_rate = 0
    if agent.profile_views > 0:
        conversion_rate = round((leads.count() / agent.profile_views) * 100, 1)

    # Calculate CRM events due today
    from core.festivals import FESTIVALS_2026
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    today_festivals = [name for name, d in FESTIVALS_2026.items() if d == today_str]
    
    today_events_count = 0
    for sub in agent.subscribers.filter(is_active=True):
        is_event_today = False
        if sub.birth_month == today.month and sub.birth_day == today.day:
            is_event_today = True
        elif sub.next_review_date == today:
            is_event_today = True
        elif today_festivals and any(f in sub.tag_list for f in today_festivals):
            is_event_today = True
            
        if is_event_today:
            today_events_count += 1

    context = {
        'agent': agent,
        'agency': agency, 
        'leads': leads,
        'section': 'stats',
        # Pass new variables to the template:
        'audience_size': audience_size,
        'broadcasts_sent': broadcasts_sent,
        'conversion_rate': conversion_rate,
        'today_events_count': today_events_count,
    }
    return render(request, 'core/dashboard_stats.html', context)

@login_required
def manage_profile(request):
    agent = request.user.agent
    if getattr(agent, 'is_bespoke', False):
        return manage_bespoke_profile(request, agent)
    if request.method == 'POST':
        form = AgentProfileForm(request.POST, request.FILES, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('manage_profile')
    else:
        form = AgentProfileForm(instance=agent)
    context = {
        'agent': agent,
        'form': form,
        'credentials': agent.credentials.all().order_by('order'),
        'section': 'profile'
    }
    return render(request, 'core/manage_profile.html', context)

@login_required
def manage_articles(request):
    agent = request.user.agent
    articles = agent.articles.all().order_by('-created_at')
    context = {
        'agent': agent,
        'articles': articles,
        'section': 'articles'
    }
    return render(request, 'core/manage_articles.html', context)

@login_required
def manage_testimonials(request):
    agent = request.user.agent
    pending_reviews = agent.testimonials.filter(is_published=False)
    published_reviews = agent.testimonials.filter(is_published=True)
    context = {
        'agent': agent,
        'pending_reviews': pending_reviews,
        'testimonials': published_reviews,
        'section': 'testimonials'
    }
    return render(request, 'core/manage_testimonials.html', context)

# ==========================================
# AGENCY BUILDER VIEW
# ==========================================
@login_required
def manage_agency_site(request):
    try:
        agency = Agency.objects.get(owner=request.user)
    except Agency.DoesNotExist:
        # Create default if missing
        agency = Agency.objects.create(owner=request.user, domain="yq-partners.com", name="YQ Partners")

    if request.method == 'POST' and 'update_settings' in request.POST:
        form = AgencySiteForm(request.POST, request.FILES, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings updated!")
            return redirect('manage_agency_site')
    else:
        form = AgencySiteForm(instance=agency)

    return render(request, 'core/manage_agency.html', {
        'form': form, 
        'agency': agency,
        'image_form': AgencyImageForm(),
        'review_form': AgencyReviewForm(),
        'section': 'agency',         # Highlights the sidebar link
        'is_agency_admin': True      # <--- THIS HIDES THE AGENT LINKS
    })
# ==========================================
# ACTION VIEWS
# ==========================================

@login_required
def create_article(request):
    agent = request.user.agent
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.agent = agent
            article.save()
            return redirect('manage_articles')
    else:
        form = ArticleForm()
    return render(request, 'core/create_article.html', {'form': form, 'title': 'Write New Article'})

@login_required
def edit_article(request, pk):
    article = get_object_or_404(Article, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            form.save()
            return redirect('manage_articles')
    else:
        form = ArticleForm(instance=article)
    return render(request, 'core/create_article.html', {'form': form, 'title': 'Edit Article'})

@login_required
def add_credential(request):
    agent = request.user.agent
    if request.method == 'POST':
        form = CredentialForm(request.POST)
        if form.is_valid():
            cred = form.save(commit=False)
            cred.agent = agent
            max_order = Credential.objects.filter(agent=agent).aggregate(Max('order'))['order__max']
            cred.order = (max_order if max_order is not None else -1) + 1
            cred.save()
            return redirect('manage_profile')
    else:
        form = CredentialForm()
    return render(request, 'core/generic_form.html', {'form': form, 'title': 'Add New Credential'})

@login_required
def delete_credential(request, pk):
    cred = get_object_or_404(Credential, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        cred.delete()
    return redirect('manage_profile')

@login_required
def add_testimonial(request):
    agent = request.user.agent
    if not agent.can_upload_testimonials:
        messages.error(request, "Your plan does not support self-uploading. Please contact support to add reviews.")
        return redirect('manage_testimonials')
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.agent = agent
            testimonial.is_published = True
            testimonial.save()
            messages.success(request, "Review added successfully!")
            return redirect('manage_testimonials')
    else:
        form = TestimonialForm()
    return render(request, 'core/add_testimonial.html', {'form': form})

@login_required
def delete_testimonial(request, pk):
    agent = request.user.agent
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=agent)
    if not agent.can_upload_testimonials:
        messages.error(request, "You cannot delete reviews on the Ad-Hoc plan. Please contact support.")
        return redirect('manage_testimonials')
    if request.method == 'POST':
        testimonial.delete()
        messages.success(request, "Review deleted.")
        return redirect('manage_testimonials')
    return render(request, 'core/delete_confirm.html', {'testimonial': testimonial})

@login_required
def edit_testimonial(request, pk):
    agent = request.user.agent
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=agent)
    if not agent.can_upload_testimonials:
        messages.error(request, "You cannot edit reviews on the Ad-Hoc plan. Please contact support.")
        return redirect('manage_testimonials')
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated.")
            return redirect('manage_testimonials')
    else:
        form = TestimonialForm(instance=testimonial)
    return render(request, 'core/edit_testimonial.html', {'form': form, 'testimonial': testimonial})

@login_required
def delete_lead(request, pk):
    lead = get_object_or_404(Lead, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        lead.delete()
    return redirect('dashboard')

from urllib.parse import quote

@login_required
def email_article_to_all(request, pk):
    agent = request.user.agent
    article = get_object_or_404(Article, pk=pk, agent=agent)
    
    if request.method == 'POST':
        subscribers = agent.subscribers.filter(is_active=True)
        valid_subs = [sub for sub in subscribers if sub.email]
        
        if not valid_subs:
            messages.error(request, "You have no active clients with valid email addresses.")
            return redirect('manage_articles')
            
        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
        article_url = f"{site_url}{reverse('article_detail', args=[article.slug])}"
        sent_count = 0
        
        for sub in valid_subs:
            client_name = sub.name or "there"
            subject = f"New Article: {article.title}"
            
            # Create a simple, clean HTML email template dynamically
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
                <p>Hi {client_name},</p>
                <p>I just published a new article that I thought you might find valuable:</p>
                <h2 style="color: #2563eb;">{article.title}</h2>
                <p style="color: #666; font-style: italic;">{strip_tags(article.content)[:200]}...</p>
                <div style="margin-top: 30px; text-align: center;">
                    <a href="{article_url}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Read Full Article</a>
                </div>
                <hr style="margin-top: 40px; border: 0; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #999;">Sent by {agent.name} via Skandage</p>
            </div>
            """
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(
                subject=subject, 
                body=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', f"{agent.name} <updates@skandage.com>"),
                to=[sub.email]
            )
            msg.attach_alternative(html_content, "text/html")
            
            try:
                msg.send(fail_silently=False)
                sent_count += 1
            except Exception as e:
                print(f"Error sending article email to {sub.email}: {e}")
                
        messages.success(request, f"Article successfully emailed to {sent_count} clients!")
        return redirect('manage_articles')
        
    return redirect('manage_articles')

@login_required
def whatsapp_article_to_all(request, pk):
    """
    Since WhatsApp doesn't allow automatic background broadcasting without the paid API,
    this generates a pre-filled forwardable message and opens the agent's WhatsApp app.
    """
    agent = request.user.agent
    article = get_object_or_404(Article, pk=pk, agent=agent)
    
    site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
    article_url = f"{site_url}{reverse('article_detail', args=[article.slug])}"
    
    message = f"Hi! I just published a new article that I thought you might find valuable:\n\n*{article.title}*\n\nRead it here: {article_url}"
    encoded_message = quote(message)
    
    # We use https://wa.me/ to trigger the app's contact selector (and bypass Django's DisallowedRedirect)
    whatsapp_url = f"https://wa.me/?text={encoded_message}"
    
    return redirect(whatsapp_url)

@login_required
def account_settings(request):
    user = request.user
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=user)
            password_form = PasswordChangeForm(user)
            if user_form.is_valid():
                user_form.save()
                return redirect('account_settings')
        elif 'change_password' in request.POST:
            user_form = UserUpdateForm(instance=user)
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user) 
                return redirect('account_settings')
    else:
        user_form = UserUpdateForm(instance=user)
        password_form = PasswordChangeForm(user)
    context = {'user_form': user_form, 'password_form': password_form, 'section': 'settings'}
    return render(request, 'core/account_settings.html', context)

def logout_view(request):
    logout(request)
    return redirect('home')

# Subpage Views
def agent_testimonials(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True)
    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    testimonials = agent.testimonials.filter(is_published=True).order_by('-is_featured', '-id')
    
    context = {
        'agent': agent,
        'testimonials': testimonials,
        'theme': theme_config
    }
    
    # VIP ARCHITECTURE INTERCEPT
    if getattr(agent, 'is_bespoke', False) and getattr(agent, 'bespoke_template_name', ''):
        context['custom_fields'] = agent.bespoke_data or {}
        # Automatically routes core/karna_custom.html -> core/karna_letters.html
        template_name = agent.bespoke_template_name.replace('_custom', '_letters')
        return render(request, template_name, context)
        
    return render(request, 'core/public_testimonials.html', context)

def agent_bio(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True)
    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    
    context = {
        'agent': agent,
        'credentials': agent.credentials.all().order_by('order'),
        'services': agent.services.all(), # Ensure services are passed to the view
        'theme': theme_config
    }
    
    # VIP ARCHITECTURE INTERCEPT
    if getattr(agent, 'is_bespoke', False) and getattr(agent, 'bespoke_template_name', ''):
        context['custom_fields'] = agent.bespoke_data or {}
        # Automatically routes core/karna_custom.html -> core/karna_expertise.html
        template_name = agent.bespoke_template_name.replace('_custom', '_expertise')
        return render(request, template_name, context)
        
    return render(request, 'core/public_bio.html', context)

def single_testimonial(request, slug, pk):
    agent = get_object_or_404(Agent, slug=slug, is_public=True) # Check Public
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=agent)
    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    return render(request, 'core/single_testimonial.html', {
        'agent': agent,
        'review': testimonial,
        'theme': theme_config
    })

@login_required
def manage_services(request):
    agent = request.user.agent
    services = agent.services.all()
    context = {'agent': agent, 'services': services, 'section': 'services'}
    return render(request, 'core/manage_services.html', context)

@login_required
def add_service(request):
    agent = request.user.agent
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.agent = agent
            service.save()
            return redirect('manage_services')
    else:
        form = ServiceForm()
    return render(request, 'core/generic_form.html', {'form': form, 'title': 'Add New Service'})

@login_required
def delete_service(request, pk):
    service = get_object_or_404(Service, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        service.delete()
    return redirect('manage_services')

@login_required
def delete_article(request, pk):
    article = get_object_or_404(Article, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        article.delete()
        messages.success(request, "Article deleted successfully.")
    return redirect('manage_articles')

@login_required
def edit_credential(request, pk):
    cred = get_object_or_404(Credential, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        form = CredentialForm(request.POST, instance=cred)
        if form.is_valid():
            form.save()
            messages.success(request, "Credential updated.")
            return redirect('manage_profile')
    else:
        form = CredentialForm(instance=cred)
    return render(request, 'core/generic_form.html', {'form': form, 'title': 'Edit Credential'})

@login_required
def toggle_testimonial_feature(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=request.user.agent)
    testimonial.is_featured = not testimonial.is_featured
    testimonial.save()
    status = "Featured" if testimonial.is_featured else "Un-featured"
    messages.success(request, f"Review marked as {status}")
    return redirect('manage_testimonials')

@login_required
@require_POST
def reorder_credentials(request):
    try:
        data = json.loads(request.body)
        ordered_ids = data.get('order', [])
        for index, cred_id in enumerate(ordered_ids):
            Credential.objects.filter(pk=cred_id, agent=request.user.agent).update(order=index)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def import_testimonials(request):
    if request.method == 'POST':
        target_url = request.POST.get('target_url')
        selector = request.POST.get('css_selector', '').strip() or '.card'
        if not target_url:
            messages.error(request, "Please provide a valid URL.")
            return redirect('manage_testimonials')
        try:
            count = scrape_and_save_testimonials(request.user.agent, target_url, selector)
            if count > 0:
                messages.success(request, f"Success! Imported {count} testimonials.")
            else:
                messages.warning(request, "Found 0 reviews. Check the CSS selector.")
        except Exception as e:
            print(f"Import Error: {e}")
            messages.error(request, "An error occurred during import.")
    return redirect('manage_testimonials')

@login_required
def manage_subscribers(request):
    agent = request.user.agent

    if request.method == 'POST':
        # --- SINGLE CLIENT ADD ---
        if 'add_subscriber' in request.POST:
            name = request.POST.get('name', '').strip()
            email_raw = request.POST.get('email', '').strip().lower()

            if not name:
                messages.error(request, "Name is required.")
                return redirect('manage_subscribers')

            # Only check for duplicates if an email is provided
            if email_raw:
                hashed = hash_email(email_raw)
                if Subscriber.objects.filter(agent=agent, email_hash=hashed).exists():
                    messages.warning(request, f"A client with that email already exists in your vault.")
                    return redirect('manage_subscribers')

            sub = Subscriber(agent=agent, name=name, source='manual')
            sub.email = email_raw  # Encrypted via model setter
            sub.save()
            messages.success(request, f"{name} has been added to your vault.")
            return redirect('manage_subscribers')

        # --- CSV/EXCEL BULK IMPORT ---
        if 'import_csv' in request.POST:
            file_obj = request.FILES.get('csv_file')
            if not file_obj or not file_obj.name.endswith(('.csv', '.xls', '.xlsx')):
                messages.error(request, "Please upload a valid .csv or .xlsx file.")
                return redirect('manage_subscribers')

            try:
                parsed_data = smart_parse_clients(file_obj)
                
                if not parsed_data:
                    messages.error(request, "Could not find any valid names or emails in this file.")
                    return redirect('manage_subscribers')

                race_display = {'C': 'Chinese', 'M': 'Malay', 'I': 'Indian', 'O': 'Others'}
                gender_display = {'M': 'Male', 'F': 'Female', 'U': 'Unspecified'}
                
                # Flag to check if we need to ask Wendy for default follow-up duration
                needs_freq_prompt = False

                for client in parsed_data:
                    existing_sub = None
                    email_raw = client.get('email', '')
                    client['race_display'] = race_display.get(client.get('race', 'O'), 'Others')
                    client['gender_display'] = gender_display.get(client.get('gender', 'U'), 'Unspecified')

                    # Preserve the original CSV 'status' column value BEFORE the
                    # duplicate-check code overwrites client['status'] to 'new'/'duplicate'.
                    # This is used later for pipeline_status mapping.
                    csv_pipeline_status = str(client.get('status', '')).lower()

                    # 1. DUPLICATE CHECKING (Secure Hash Lookups)
                    if email_raw:
                        hashed = hash_email(email_raw)
                        existing_sub = Subscriber.objects.filter(agent=agent, email_hash=hashed).first()
                    else:
                        imported_name = client.get('name', '').strip()
                        if imported_name:
                            name_hashed = hashlib.sha256(imported_name.lower().encode()).hexdigest()
                            existing_sub = Subscriber.objects.filter(agent=agent, name_hash=name_hashed).first()

                    if existing_sub:
                        client['status'] = 'duplicate'
                        client['existing_name'] = existing_sub.name
                        client['existing_dob'] = existing_sub.date_of_birth.strftime('%d/%m/%Y') if existing_sub.date_of_birth else '—'
                        client['existing_race'] = race_display.get(existing_sub.race, 'Others')
                        client['existing_gender'] = gender_display.get(existing_sub.gender, 'Unspecified')
                        client['action'] = 'skip'
                    else:
                        client['status'] = 'new'
                        client['action'] = 'add'

                    # 2. HQ PARITY & SMART DATE PARSER INTEGRATION
                    # utils_import returns lowercase keys; fall back to raw capitalised
                    # names so this works for any future custom parser too.
                    client['phone'] = str(
                        client.get('phone') or client.get('Phone') or client.get('Mobile') or ''
                    )
                    client['address'] = str(
                        client.get('address') or client.get('Address') or client.get('Address 1') or ''
                    )
                    client['notes'] = str(
                        client.get('notes') or client.get('Notes') or client.get('Contact Notes') or ''
                    )

                    # Map Pipeline Status using the ORIGINAL csv status value (not 'new'/'duplicate')
                    client['pipeline_status'] = 'prospect' if 'prospect' in csv_pipeline_status else 'client'

                    # --- SMART REVIEW DATE PARSER ---
                    # Priority 1: Direct "Next Review Date" column → use as-is
                    next_review = (
                        client.get('next_review_date') or
                        client.get('Next Review Date')
                    )
                    # Priority 2: "Last Updated/Review" + "Review Freq" → calculate
                    last_updated = (
                        client.get('last_review') or
                        client.get('Last Updated') or
                        client.get('Last Review Date')
                    )
                    review_freq = (
                        client.get('review_freq') or
                        client.get('Review Freq (months)')
                    )

                    if next_review:
                        client['next_review_date_calc'] = next_review
                    elif last_updated and review_freq:
                        # Now this will work because we added the helper above!
                        client['next_review_date_calc'] = add_months_to_date(last_updated, review_freq)
                    elif last_updated:
                        needs_freq_prompt = True
                        client['last_updated_for_calc'] = last_updated

                # Pass data and flags to the preview session
                request.session['pending_import'] = parsed_data
                request.session['needs_freq_prompt'] = needs_freq_prompt
                return redirect('preview_import')

            except Exception as e:
                messages.error(request, f"Could not read the file. Error: {str(e)}")
                return redirect('manage_subscribers')

    # --- GET: SEARCH & RENDER ---
    query = request.GET.get('q', '').strip().lower()
    # Fetch active subscribers and order by most recent add
    all_subscribers = agent.subscribers.filter(is_active=True).order_by('-created_at')
    
    if query:
        # SECURE: In-Memory Filtering (Database columns are encrypted/blind)
        subscribers = []
        for sub in all_subscribers:
            safe_tags = sub.tags.lower() if sub.tags else ""
            safe_name = sub.name.lower() if sub.name else ""
            
            if query in safe_name or query in safe_tags:
                subscribers.append(sub)
    else:
        subscribers = list(all_subscribers)

    return render(request, 'core/manage_subscribers.html', {
        'agent': agent,
        'subscribers': subscribers,
        'section': 'audience',
        'query': query,
        'today': date.today().strftime('%Y-%m-%d'),
    })
@login_required
def preview_import(request):
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        return redirect('dashboard')

    # Fetch the parsed data and the frequency prompt flag from the session
    pending_import = request.session.get('pending_import')
    needs_freq_prompt = request.session.get('needs_freq_prompt', False)

    if not pending_import:
        messages.warning(request, "No pending import found. Please upload your file again.")
        return redirect('manage_subscribers')

    if request.method == 'POST':
        import uuid
        import hashlib
        from datetime import datetime
        
        # Get the fallback duration from the form prompt (Default to 12 if missing)
        default_freq = request.POST.get('default_freq', 12)
        
        added_count = 0
        updated_count = 0
        skipped_count = 0

        for i, client_data in enumerate(pending_import):
            action = request.POST.get(f'action_{i}', 'skip')
            email_raw = client_data.get('email', '')
            dob_raw = client_data.get('dob_db') or None
            
            # --- DATE CONVERSION: DOB ---
            dob_value = None
            if dob_raw:
                try:
                    dob_value = datetime.strptime(str(dob_raw), '%Y-%m-%d').date()
                except ValueError:
                    dob_value = None

            # --- SMART PARSER: NEXT REVIEW DATE ---
            next_review_val = None
            last_review_val = None
            freq_months_val = None
            calc_date_str = client_data.get('next_review_date_calc')
            last_updated_str = client_data.get('last_updated_for_calc') or client_data.get('last_review')

            # Parse last_review_date for storage
            if last_updated_str:
                try:
                    last_review_val = datetime.strptime(str(last_updated_str).strip(), '%Y-%m-%d').date()
                except ValueError:
                    pass

            # Parse review_freq_months for storage
            raw_freq = client_data.get('review_freq') or default_freq
            try:
                freq_months_val = int(float(str(raw_freq)))
            except (ValueError, TypeError):
                freq_months_val = None

            if calc_date_str:
                try:
                    next_review_val = datetime.strptime(str(calc_date_str), '%Y-%m-%d').date()
                except ValueError:
                    pass
            elif last_updated_str:
                # Calculate using file frequency or user-provided default
                calc_fallback = add_months_to_date(last_updated_str, raw_freq)
                if calc_fallback:
                    try:
                        next_review_val = datetime.strptime(calc_fallback, '%Y-%m-%d').date()
                    except ValueError:
                        pass

            if action == 'skip':
                skipped_count += 1
                continue

            elif action == 'add':
                if email_raw:
                    hashed = hash_email(email_raw)
                    if Subscriber.objects.filter(agent=agent, email_hash=hashed).exists():
                        skipped_count += 1
                        continue

                # --- BUILD WITH ONLY PLAIN MODEL FIELDS IN CONSTRUCTOR ---
                # IMPORTANT: Do NOT pass encrypted properties (name, race, gender,
                # date_of_birth) as constructor kwargs. Django's Model.__init__ does
                # not reliably call @property setters when multiple property kwargs are
                # mixed with model field kwargs — the encrypted fields end up as b''
                # (empty). Set every encrypted field explicitly AFTER construction.
                sub = Subscriber(
                    agent=agent,
                    source='csv_import',
                    pipeline_status=client_data.get('pipeline_status', 'client'),
                    next_review_date=next_review_val,
                    last_review_date=last_review_val,
                    review_freq_months=freq_months_val,
                )
                # Set all encrypted / property fields explicitly
                sub.name = client_data.get('name', '')
                sub.race = client_data.get('race', 'O')
                sub.gender = client_data.get('gender', 'U')
                sub.date_of_birth = dob_value
                sub.email = email_raw
                sub.phone = client_data.get('phone', '')
                sub.address = client_data.get('address', '')
                sub.notes = client_data.get('notes', '')
                sub.save()
                added_count += 1

            elif action == 'replace':
                existing_sub = None
                if email_raw:
                    hashed = hash_email(email_raw)
                    existing_sub = Subscriber.objects.filter(agent=agent, email_hash=hashed).first()
                else:
                    imported_name = client_data.get('name', '').strip()
                    if imported_name:
                        name_hashed = hashlib.sha256(imported_name.lower().encode()).hexdigest()
                        existing_sub = Subscriber.objects.filter(agent=agent, name_hash=name_hashed).first()

                if existing_sub:
                    if client_data.get('name'): existing_sub.name = client_data.get('name')
                    if dob_value is not None: existing_sub.date_of_birth = dob_value
                    if client_data.get('race'): existing_sub.race = client_data.get('race')
                    if client_data.get('gender'): existing_sub.gender = client_data.get('gender')

                    # Update HQ & Review Fields
                    existing_sub.pipeline_status = client_data.get('pipeline_status', 'client')
                    if next_review_val: existing_sub.next_review_date = next_review_val
                    if last_review_val: existing_sub.last_review_date = last_review_val
                    if freq_months_val: existing_sub.review_freq_months = freq_months_val
                    if client_data.get('phone'): existing_sub.phone = client_data.get('phone')
                    if client_data.get('address'): existing_sub.address = client_data.get('address')
                    if client_data.get('notes'): existing_sub.notes = client_data.get('notes')

                    existing_sub.save()
                    updated_count += 1

        # Clear session data after successful import
        if 'pending_import' in request.session: del request.session['pending_import']
        if 'needs_freq_prompt' in request.session: del request.session['needs_freq_prompt']
        
        messages.success(request, f"Vault updated: {added_count} added, {updated_count} updated, {skipped_count} skipped.")
        return redirect('manage_subscribers')

    # GET: Build summary stats for the UI
    new_count = sum(1 for c in pending_import if c.get('status') == 'new')
    duplicate_count = sum(1 for c in pending_import if c.get('status') == 'duplicate')
    race_chinese = sum(1 for c in pending_import if c.get('race') == 'C')
    race_malay = sum(1 for c in pending_import if c.get('race') == 'M')
    race_indian = sum(1 for c in pending_import if c.get('race') == 'I')
    race_others = sum(1 for c in pending_import if c.get('race') == 'O')

    return render(request, 'core/preview_import.html', {
        'pending_import': pending_import,
        'section': 'audience',
        'new_count': new_count,
        'duplicate_count': duplicate_count,
        'race_chinese': race_chinese,
        'race_malay': race_malay,
        'race_indian': race_indian,
        'race_others': race_others,
        'needs_freq_prompt': needs_freq_prompt,
    })
@login_required
def newsletter_dashboard(request):
    agent = request.user.agent
    newsletters = agent.newsletters.all().order_by('-created_at')
    audience_count = agent.subscribers.filter(is_active=True).count()
    return render(request, 'core/newsletter_dashboard.html', {'newsletters': newsletters, 'audience_count': audience_count, 'section': 'broadcasts'})
@login_required
def compose_newsletter(request):
    agent = request.user.agent
    if request.method == 'POST':
        subject = request.POST.get('subject')
        content = request.POST.get('content') 
        attachment = request.FILES.get('attachment') 
        html_file = request.FILES.get('html_file') # <--- NEW
        
        Newsletter.objects.create(
            agent=agent, 
            subject=subject, 
            content=content,
            attachment=attachment,
            html_file=html_file # <--- NEW
        )
        messages.success(request, "Broadcast saved as draft.")
        return redirect('newsletter_dashboard')
        
    return render(request, 'core/compose_newsletter.html', {'section': 'broadcasts'})

@login_required
def send_newsletter(request, pk):
    agent = request.user.agent
    newsletter = get_object_or_404(Newsletter, pk=pk, agent=agent)
    
    subscribers = agent.subscribers.filter(is_active=True)
    if not subscribers.exists():
        messages.error(request, "You have no active subscribers.")
        return redirect('newsletter_dashboard')

    if newsletter.status == 'sent':
        messages.error(request, "This broadcast has already been sent.")
        return redirect('newsletter_dashboard')

    from_email = f"{agent.name} <updates@skandage.com>"
    messages_to_send = []
    
    # ---------------------------------------------------------
    # 1. READ THE PDF SAFELY (IF IT EXISTS)
    # ---------------------------------------------------------
    file_content = None
    file_name = ""
    pdf_url = ""
    
    if newsletter.attachment:
        try:
            # Build the absolute URL so we can link to it in the email body
            pdf_url = request.build_absolute_uri(newsletter.attachment.url)
            
            # Open and read the file from the database safely
            newsletter.attachment.open()
            file_content = newsletter.attachment.read()
            file_name = newsletter.attachment.name.split('/')[-1]
            newsletter.attachment.close()
        except Exception as e:
            print(f"Attachment Read Error: {e}")

    # ---------------------------------------------------------
    # 1.5 READ THE CUSTOM HTML FILE (IF IT EXISTS)
    # ---------------------------------------------------------
    custom_html_template = ""
    # Check if the model actually has the html_file field defined and uploaded
    if hasattr(newsletter, 'html_file') and newsletter.html_file:
        try:
            newsletter.html_file.open()
            # Read the bytes and decode to a string
            custom_html_template = newsletter.html_file.read().decode('utf-8', errors='ignore')
            newsletter.html_file.close()
        except Exception as e:
            print(f"HTML File Read Error: {e}")

    # ---------------------------------------------------------
    # 2. BUILD THE EMAILS
    # ---------------------------------------------------------
    for sub in subscribers:
        client_name = sub.name or "there"
        
        # If there's a PDF, generate a massive, beautiful button
        pdf_button_html = ""
        if pdf_url:
            pdf_button_html = f"""
            <div style="text-align: center; margin: 30px 0;">
                <a href="{pdf_url}" target="_blank" style="background-color: #2563eb; color: #ffffff; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    📄 View Full PDF Newsletter
                </a>
            </div>
            """

        # --- LOGIC: CHOOSE BETWEEN HTML FILE OR TEXT EDITOR ---
        if custom_html_template:
            # Use the uploaded HTML file, allow dynamic name insertion
            html_message = custom_html_template.replace('{{ client_name }}', client_name)
            if pdf_button_html:
                html_message += pdf_button_html # Append button to the bottom if PDF exists
        else:
            # Use the standard Text Editor fallback
            html_message = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; color: #1c1917; line-height: 1.6;">
                <p>Hi {client_name},</p>
                {newsletter.content}
                {pdf_button_html}
                <br>
                <p>Best regards,<br><strong>{agent.name}</strong><br>{agent.title} at {agent.company}</p>
            </div>
            """
        
        text_message = strip_tags(html_message)
        
        msg = EmailMultiAlternatives(
            subject=newsletter.subject,
            body=text_message,
            from_email=from_email,
            to=[sub.email]
        )
        msg.attach_alternative(html_message, "text/html")
        
        # ---------------------------------------------------------
        # 3. ATTACH AS INLINE (Triggers Apple Mail's Native Preview)
        # ---------------------------------------------------------
        if file_content:
            mime_pdf = MIMEApplication(file_content, _subtype="pdf")
            # 'inline' tells the email client to try and display it in the body!
            mime_pdf.add_header('Content-Disposition', 'inline', filename=file_name)
            msg.attach(mime_pdf)
            
        messages_to_send.append(msg)

    # ---------------------------------------------------------
    # 4. SEND BATCH
    # ---------------------------------------------------------
    try:
        connection = get_connection()
        connection.send_messages(messages_to_send)

        newsletter.status = 'sent'
        newsletter.sent_at = timezone.now()
        newsletter.save()
        messages.success(request, f"Blast off! Sent to {subscribers.count()} clients.")
    except Exception as e:
        messages.error(request, f"Failed to send. Error: {str(e)}")

    return redirect('newsletter_dashboard')


# ===========================================================================
# SUBSCRIBER EDIT & DELETE
# ===========================================================================
@login_required
def edit_subscriber(request, pk):
    agent = request.user.agent
    subscriber = get_object_or_404(Subscriber, pk=pk, agent=agent)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email_raw = request.POST.get('email', '').strip().lower()
        dob_raw = request.POST.get('date_of_birth', '').strip()
        race = request.POST.get('race', 'O')
        gender = request.POST.get('gender', 'U')

        if not name:
            messages.error(request, "Name is required.")
            return redirect('manage_subscribers')

        subscriber.name = name
        subscriber.race = race
        subscriber.gender = gender
        subscriber.tags = request.POST.get('tags', '').strip()
        subscriber.phone = request.POST.get('phone', '').strip()
        subscriber.address = request.POST.get('address', '').strip()

        # Handle DOB
        if dob_raw:
            try:
                from datetime import datetime
                subscriber.date_of_birth = datetime.strptime(dob_raw, '%Y-%m-%d').date()
            except ValueError:
                subscriber.date_of_birth = None
        else:
            subscriber.date_of_birth = None

        # Handle email change
        current_email = subscriber.email  # decrypts existing
        if email_raw and email_raw != current_email:
            hashed = hash_email(email_raw)
            if Subscriber.objects.filter(agent=agent, email_hash=hashed).exclude(pk=pk).exists():
                messages.error(request, "A client with that email already exists in your vault.")
                return redirect('manage_subscribers')
            subscriber.email = email_raw
        elif not email_raw and current_email:
            # Setting it to blank allows the setter to handle it securely
            subscriber.email = ""

        # Handle next_review_date
        nrd_raw = request.POST.get('next_review_date', '').strip()
        if nrd_raw:
            try:
                subscriber.next_review_date = datetime.strptime(nrd_raw, '%Y-%m-%d').date()
            except ValueError:
                subscriber.next_review_date = None
        else:
            subscriber.next_review_date = None

        # Handle last_review_date
        lrd_raw = request.POST.get('last_review_date', '').strip()
        if lrd_raw:
            try:
                subscriber.last_review_date = datetime.strptime(lrd_raw, '%Y-%m-%d').date()
            except ValueError:
                subscriber.last_review_date = None
        else:
            subscriber.last_review_date = None

        # Handle review_freq_months
        freq_raw = request.POST.get('review_freq_months', '').strip()
        try:
            subscriber.review_freq_months = int(freq_raw) if freq_raw else None
        except ValueError:
            subscriber.review_freq_months = None

        subscriber.save()
        messages.success(request, f"✓ {subscriber.name} has been updated.")
        return redirect('manage_subscribers')

    return render(request, 'core/edit_subscriber.html', {
        'sub': subscriber,
        'section': 'audience'
    })


@login_required
@require_POST
def mass_update_review_freq(request):
    """
    Bulk-update review_freq_months for all subscribers of this agent.
    Recalculates next_review_date = last_review_date + new_freq for each subscriber
    that has a stored last_review_date. For those without one, it uses today's date.
    """
    agent = request.user.agent
    try:
        new_freq = int(request.POST.get('new_freq', 0))
    except (ValueError, TypeError):
        messages.error(request, "Invalid frequency entered.")
        return redirect('manage_subscribers')

    if new_freq < 1:
        messages.error(request, "Frequency must be at least 1 month.")
        return redirect('manage_subscribers')

    updated = 0
    for sub in agent.subscribers.filter(is_active=True):
        sub.review_freq_months = new_freq
        base_date = sub.last_review_date or date.today()
        new_review_date_str = add_months_to_date(base_date.strftime('%Y-%m-%d'), new_freq)
        if new_review_date_str:
            try:
                sub.next_review_date = datetime.strptime(new_review_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        sub.save()
        updated += 1

    messages.success(request, f"Updated review frequency to {new_freq} months for {updated} clients.")
    return redirect('manage_subscribers')


@login_required
@require_POST
def send_review_reminder(request, pk):
    """Send a review reminder email to a single subscriber."""
    agent = request.user.agent
    subscriber = get_object_or_404(Subscriber, pk=pk, agent=agent)

    if not subscriber.email:
        messages.error(request, f"{subscriber.name} has no email address on file.")
        return redirect('upcoming_events')

    site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
    agent_headshot_url = f"{site_url}{agent.headshot.url}" if agent.headshot else ""

    context = {
        'client_name': subscriber.name,
        'agent': agent,
        'next_review_date': subscriber.next_review_date,
        'agent_headshot_url': agent_headshot_url,
        'site_url': site_url,
    }
    html_content = render_to_string('core/emails/review_reminder_email.html', context)
    text_content = strip_tags(html_content)
    subject = f"Your Annual Review is Coming Up — {subscriber.name}"

    from_email = getattr(
        settings, 'DEFAULT_FROM_EMAIL',
        f"{agent.name} <updates@skandage.com>"
    )
    msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=from_email, to=[subscriber.email])
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send(fail_silently=False)
        messages.success(request, f"Review reminder sent to {subscriber.name}.")
    except Exception as e:
        messages.error(request, f"Failed to send email: {str(e)}")

    return redirect('upcoming_events')


@login_required
@require_POST
def send_bulk_review_reminders(request):
    """Send review reminder emails to multiple subscribers at once."""
    agent = request.user.agent
    sub_ids = request.POST.getlist('subscriber_ids')

    if not sub_ids:
        messages.error(request, "No clients selected.")
        return redirect('upcoming_events')

    site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
    agent_headshot_url = f"{site_url}{agent.headshot.url}" if agent.headshot else ""
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"{agent.name} <updates@skandage.com>")

    sent = 0
    failed = 0
    for sub in Subscriber.objects.filter(pk__in=sub_ids, agent=agent, is_active=True):
        if not sub.email:
            failed += 1
            continue
        context = {
            'client_name': sub.name,
            'agent': agent,
            'next_review_date': sub.next_review_date,
            'agent_headshot_url': agent_headshot_url,
            'site_url': site_url,
        }
        html_content = render_to_string('core/emails/review_reminder_email.html', context)
        text_content = strip_tags(html_content)
        subject = f"Your Annual Review is Coming Up — {sub.name}"
        msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=from_email, to=[sub.email])
        msg.attach_alternative(html_content, "text/html")
        try:
            msg.send(fail_silently=False)
            sent += 1
        except Exception:
            failed += 1

    if sent:
        messages.success(request, f"Review reminders sent to {sent} client(s).")
    if failed:
        messages.warning(request, f"{failed} client(s) could not be emailed (missing address or send error).")

    return redirect('upcoming_events')


@login_required
def delete_subscriber(request, pk):
    agent = request.user.agent
    subscriber = get_object_or_404(Subscriber, pk=pk, agent=agent)

    if request.method == 'POST':
        name = subscriber.name
        subscriber.delete()
        messages.success(request, f"'{name}' has been removed from your vault.")

    return redirect('manage_subscribers')


# ===========================================================================
# CRM — BIRTHDAY CARDS MANAGEMENT
# ===========================================================================

# Maps occasion names to their demographic association (for UI display)
OCCASION_DEMOGRAPHIC_MAP = {
    'Birthday': {'label': 'Universal', 'color': 'amber', 'emoji': '🎂'},
    'Lunar New Year': {'label': 'Chinese', 'color': 'red', 'emoji': '🧧'},
    'Mid-Autumn Festival': {'label': 'Chinese', 'color': 'orange', 'emoji': '🥮'},
    'Deepavali': {'label': 'Indian', 'color': 'purple', 'emoji': '🪔'},
    'Pongal': {'label': 'Indian', 'color': 'yellow', 'emoji': '🌾'},
    'Hari Raya Aidilfitri': {'label': 'Malay', 'color': 'emerald', 'emoji': '🌙'},
    'Hari Raya Haji': {'label': 'Malay', 'color': 'teal', 'emoji': '🕌'},
    'Christmas': {'label': 'Universal', 'color': 'green', 'emoji': '🎄'},
    'New Year': {'label': 'Universal', 'color': 'blue', 'emoji': '🎆'},
    'Other': {'label': 'Custom', 'color': 'slate', 'emoji': '🎉'},
}


@login_required
def manage_cards(request):
    agent = request.user.agent

    if request.method == 'POST' and 'add_card' in request.POST:
        name = request.POST.get('name', '').strip()
        occasion = request.POST.get('occasion', '').strip()
        default_message = request.POST.get('default_message', '').strip()
        target_gender = request.POST.get('target_gender', 'A')
        try:
            target_age_min = int(request.POST.get('target_age_min', 0))
            target_age_max = int(request.POST.get('target_age_max', 120))
        except (ValueError, TypeError):
            target_age_min, target_age_max = 0, 120
        image = request.FILES.get('image')

        if not name or not occasion:
            messages.error(request, "Card name and occasion are required.")
            return redirect('manage_cards')

        card = CardTemplate(
            agent=agent,
            name=name,
            occasion=occasion,
            default_message=default_message or "Wishing you joy and happiness on this special occasion!",
            target_gender=target_gender,
            target_age_min=target_age_min,
            target_age_max=target_age_max,
            is_active=True,
        )
        if image:
            card.image = image
        card.save()
        messages.success(request, f"✓ Card design '{name}' added to your library.")
        return redirect('manage_cards')

    # Build card queryset with demographic metadata
    cards = CardTemplate.objects.filter(agent=agent, is_active=True).order_by('occasion', 'name')

    # Enrich each card with UI metadata
    enriched_cards = []
    for card in cards:
        demo_info = OCCASION_DEMOGRAPHIC_MAP.get(card.occasion, OCCASION_DEMOGRAPHIC_MAP['Other'])
        enriched_cards.append({
            'card': card,
            'demo_label': demo_info['label'],
            'demo_color': demo_info['color'],
            'demo_emoji': demo_info['emoji'],
        })

    # Summary stats
    occasions_used = list(cards.values_list('occasion', flat=True).distinct())
    total_cards = cards.count()

    return render(request, 'core/manage_cards.html', {
        'agent': agent,
        'enriched_cards': enriched_cards,
        'all_occasion_choices': [c[0] for c in CardTemplate.OCCASION_CHOICES],
        'occasions_used': occasions_used,
        'total_cards': total_cards,
        'section': 'crm',
        'occasion_demographic_map': OCCASION_DEMOGRAPHIC_MAP,
    })


@login_required
def edit_card(request, pk):
    agent = request.user.agent
    card = get_object_or_404(CardTemplate, pk=pk, agent=agent)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        occasion = request.POST.get('occasion', '').strip()
        default_message = request.POST.get('default_message', '').strip()
        target_gender = request.POST.get('target_gender', 'A')
        try:
            target_age_min = int(request.POST.get('target_age_min', 0))
            target_age_max = int(request.POST.get('target_age_max', 120))
        except (ValueError, TypeError):
            target_age_min, target_age_max = card.target_age_min, card.target_age_max
        image = request.FILES.get('image')

        if not name or not occasion:
            messages.error(request, "Card name and occasion are required.")
        else:
            card.name = name
            card.occasion = occasion
            card.default_message = default_message
            card.target_gender = target_gender
            card.target_age_min = target_age_min
            card.target_age_max = target_age_max
            if image:
                card.image = image
            card.save()
            messages.success(request, f"✓ '{name}' has been updated.")

    return redirect('manage_cards')


@login_required
def delete_card(request, pk):
    agent = request.user.agent
    card = get_object_or_404(CardTemplate, pk=pk, agent=agent)

    if request.method == 'POST':
        name = card.name
        card.delete()
        messages.success(request, f"Card design '{name}' deleted.")

    return redirect('manage_cards')


@login_required
def upcoming_events(request):
    agent = request.user.agent
    today = date.today()

    FESTIVAL_DATES = {
        'New Year': date(today.year, 1, 1),
        'Pongal': date(today.year, 1, 14),
        'Lunar New Year': date(2026, 2, 17),
        'Hari Raya Aidilfitri': date(2026, 3, 20),
        'Hari Raya Haji': date(2026, 5, 27),
        'Mid-Autumn Festival': date(2026, 9, 25),
        'Deepavali': date(2026, 11, 8),
        'Christmas': date(today.year, 12, 25),
    }

    if request.method == 'POST':
        # ==========================================
        # BATCH SEND LOGIC
        # ==========================================
        if 'batch_send' in request.POST:
            batch_data_list = request.POST.getlist('batch_data')
            custom_message = request.POST.get('batch_custom_message', '').strip()
            sent_count = 0
            
            for data_string in batch_data_list:
                try:
                    # Parse the payload from the checkbox
                    sub_id, temp_id, occasion_type, event_date_str = data_string.split('|')
                    sub = Subscriber.objects.get(pk=sub_id, agent=agent)
                    template = CardTemplate.objects.get(pk=temp_id, agent=agent)
                    
                    if sub.email:
                        if occasion_type == 'Birthday':
                            subject = f"Happy Birthday, {sub.name}!"
                            emoji = '🎂'
                        else:
                            subject = f"Happy {occasion_type}, {sub.name}!"
                            # Safe dictionary lookup without requiring settings import
                            from core.views import OCCASION_DEMOGRAPHIC_MAP
                            emoji = OCCASION_DEMOGRAPHIC_MAP.get(occasion_type, {}).get('emoji', '🎉')

                        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
                        image_url = f"{site_url}{template.image.url}" if template.image else ""
                        agent_headshot_url = f"{site_url}{agent.headshot.url}" if agent.headshot else ""
                        
                        context = {
                            'client_name': sub.name,
                            'agent': agent,
                            'occasion': occasion_type,
                            'message': custom_message or template.default_message, 
                            'card_image_url': image_url,
                            'agent_headshot_url': agent_headshot_url,
                            'occasion_emoji': emoji
                        }
                        
                        html_content = render_to_string('core/emails/card_email.html', context)
                        text_content = strip_tags(html_content)
                        
                        msg = EmailMultiAlternatives(
                            subject=subject, body=text_content,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', f"{agent.name} <updates@skandage.com>"),
                            to=[sub.email]
                        )
                        msg.attach_alternative(html_content, "text/html")
                        
                        msg.send(fail_silently=False)
                        
                        scheduled_date = datetime.strptime(event_date_str, '%Y-%m-%d').date() if event_date_str else today
                        CardLog.objects.create(
                            agent=agent, subscriber=sub, card_template=template,
                            occasion=occasion_type, status='sent', scheduled_date=scheduled_date,
                            sent_at=timezone.now()
                        )
                        sent_count += 1
                except Exception as e:
                    print(f"Batch Send Error: {e}")
                    
            messages.success(request, f"Batch processed successfully! Sent {sent_count} personalized cards.")
            return redirect('upcoming_events')

        # ==========================================
        # SINGLE SEND LOGIC
        # ==========================================
        else:
            sub_id = request.POST.get('subscriber_id')
            template_id = request.POST.get('template_id')
            custom_message = request.POST.get('custom_message', '').strip()
            occasion_type = request.POST.get('occasion_type', 'Birthday')
            event_date_str = request.POST.get('event_date')
            
            sub = get_object_or_404(Subscriber, pk=sub_id, agent=agent)
            template = get_object_or_404(CardTemplate, pk=template_id, agent=agent)
            
            if sub.email:
                if occasion_type == 'Birthday':
                    subject = f"Happy Birthday, {sub.name}!"
                    emoji = '🎂'
                else:
                    subject = f"Happy {occasion_type}, {sub.name}!"
                    from core.views import OCCASION_DEMOGRAPHIC_MAP
                    emoji = OCCASION_DEMOGRAPHIC_MAP.get(occasion_type, {}).get('emoji', '🎉')

                site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/')[:-1])
                image_url = f"{site_url}{template.image.url}" if template.image else ""
                agent_headshot_url = f"{site_url}{agent.headshot.url}" if agent.headshot else ""
                
                context = {
                    'client_name': sub.name, 'agent': agent, 'occasion': occasion_type,
                    'message': custom_message or template.default_message, 
                    'card_image_url': image_url, 'agent_headshot_url': agent_headshot_url, 'occasion_emoji': emoji
                }
                
                html_content = render_to_string('core/emails/card_email.html', context)
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(
                    subject=subject, body=text_content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', f"{agent.name} <updates@skandage.com>"),
                    to=[sub.email]
                )
                msg.attach_alternative(html_content, "text/html")
                
                try:
                    msg.send(fail_silently=False)
                    scheduled_date = datetime.strptime(event_date_str, '%Y-%m-%d').date() if event_date_str else today
                    CardLog.objects.create(
                        agent=agent, subscriber=sub, card_template=template,
                        occasion=occasion_type, status='sent', scheduled_date=scheduled_date,
                        sent_at=timezone.now()
                    )
                    messages.success(request, f"Personalized {occasion_type} card sent to {sub.name}!")
                except Exception as e:
                    messages.error(request, f"Failed to send: {str(e)}")
            else:
                messages.error(request, f"{sub.name} has no valid email address.")
                
            return redirect('upcoming_events')

    # --- GET: CALCULATE UPCOMING EVENTS ---
    REVIEW_WINDOW_DAYS = 90   # show reviews due in the next 90 days
    CARD_WINDOW_DAYS = 30     # show birthdays/festivals in the next 30 days

    upcoming_list = []    # birthdays + festivals
    reviews_list = []     # upcoming policy reviews
    unique_occasions = set()

    for sub in agent.subscribers.filter(is_active=True):
        
        # 0. CHECK UPCOMING REVIEWS
        if sub.next_review_date:
            days_until_review = (sub.next_review_date - today).days
            if 0 <= days_until_review <= REVIEW_WINDOW_DAYS:
                # Build WhatsApp link using client's phone
                wa_url = ''
                if sub.phone:
                    phone_digits = ''.join(filter(str.isdigit, sub.phone))
                    if phone_digits:
                        wa_url = f"https://wa.me/{phone_digits}"
                reviews_list.append({
                    'subscriber': sub,
                    'days_until': days_until_review,
                    'event_date': sub.next_review_date,
                    'last_review_date': sub.last_review_date,
                    'review_freq_months': sub.review_freq_months,
                    'wa_url': wa_url,
                })

        # 1. CHECK BIRTHDAYS
        if sub.birth_month and sub.birth_day:
            try: bday_this_year = date(today.year, sub.birth_month, sub.birth_day)
            except ValueError: bday_this_year = date(today.year, 3, 1)
                
            if bday_this_year < today:
                try: next_bday = date(today.year + 1, sub.birth_month, sub.birth_day)
                except ValueError: next_bday = date(today.year + 1, 3, 1)
            else:
                next_bday = bday_this_year
            
            days_until = (next_bday - today).days
            
            if 0 <= days_until <= CARD_WINDOW_DAYS:
                age_turning = next_bday.year - sub.date_of_birth.year if sub.date_of_birth else 0

                if not CardLog.objects.filter(agent=agent, subscriber=sub, occasion='Birthday', scheduled_date=next_bday, status='sent').exists():
                    template = CardTemplate.objects.filter(
                        agent=agent, occasion='Birthday', is_active=True
                    ).filter(Q(target_gender='A') | Q(target_gender=sub.gender)
                    ).filter(target_age_min__lte=age_turning, target_age_max__gte=age_turning).first()

                    wa_url = ''
                    if sub.phone:
                        phone_digits = ''.join(filter(str.isdigit, sub.phone))
                        if phone_digits:
                            wa_url = f"https://wa.me/{phone_digits}"

                    upcoming_list.append({
                        'subscriber': sub, 'occasion': 'Birthday', 'days_until': days_until,
                        'event_date': next_bday, 'details': f"Turning {age_turning}" if age_turning > 0 else "Birthday",
                        'template': template, 'wa_url': wa_url,
                    })
                    unique_occasions.add('Birthday')

        # 2. CHECK FESTIVALS
        for tag in sub.tag_list:
            if tag in FESTIVAL_DATES:
                fest_date = FESTIVAL_DATES[tag]

                if fest_date < today and tag in ['New Year', 'Christmas', 'Pongal']:
                    fest_date = date(today.year + 1, fest_date.month, fest_date.day)

                days_until_fest = (fest_date - today).days

                if 0 <= days_until_fest <= CARD_WINDOW_DAYS:
                    if not CardLog.objects.filter(agent=agent, subscriber=sub, occasion=tag, scheduled_date=fest_date, status='sent').exists():
                        current_age = sub.age if sub.age else 0
                        template = CardTemplate.objects.filter(
                            agent=agent, occasion=tag, is_active=True
                        ).filter(Q(target_gender='A') | Q(target_gender=sub.gender)
                        ).filter(target_age_min__lte=current_age, target_age_max__gte=current_age).first()

                        wa_url = ''
                        if sub.phone:
                            phone_digits = ''.join(filter(str.isdigit, sub.phone))
                            if phone_digits:
                                wa_url = f"https://wa.me/{phone_digits}"

                        upcoming_list.append({
                            'subscriber': sub, 'occasion': tag, 'days_until': days_until_fest,
                            'event_date': fest_date, 'details': "Festive Greeting",
                            'template': template, 'wa_url': wa_url,
                        })
                        unique_occasions.add(tag)
            
    upcoming_list.sort(key=lambda x: x['days_until'])
    reviews_list.sort(key=lambda x: x['days_until'])

    return render(request, 'core/upcoming_events.html', {
        'upcoming': upcoming_list,
        'reviews': reviews_list,
        'unique_occasions': sorted(list(unique_occasions)),
        'section': 'crm',
        'review_window_days': 90,
        'card_window_days': 30,
    })

def onboarding_form_view(request):
    if request.method == 'POST':
        try:
            # Create the pending profile from form data
            PendingAgentOnboarding.objects.create(
                full_name=request.POST.get('full_name'),
                email=request.POST.get('email'),
                phone_number=request.POST.get('phone_number'),
                agency_name=request.POST.get('agency_name', 'AIAFA'),
                job_title=request.POST.get('job_title', 'Financial Consultant'),
                requested_subdomain=request.POST.get('requested_subdomain'),
                bio=request.POST.get('bio', ''),
                existing_website=request.POST.get('existing_website', ''),
                linkedin=request.POST.get('linkedin', ''),
                instagram=request.POST.get('instagram', ''),
                facebook=request.POST.get('facebook', ''),
                headshot=request.FILES.get('headshot'),
                credentials_upload=request.FILES.get('credentials_upload')
            )
            # You can add a quick email notification to yourself here later!
            return render(request, 'core/onboarding_success.html')
            
        except Exception as e:
            messages.error(request, f"There was an error submitting your profile: {str(e)}")
            return redirect('onboarding_form_view')

    return render(request, 'core/onboarding_form.html')

@login_required
def manage_profile(request):
    agent = request.user.agent
    
    # 1. Intercept VIP clients and send them to their custom control panel
    if getattr(agent, 'is_bespoke', False):
        return manage_bespoke_profile(request, agent)

    # 2. Standard Logic for normal users...
    if request.method == 'POST':
        form = AgentProfileForm(request.POST, request.FILES, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('manage_profile')
    else:
        form = AgentProfileForm(instance=agent)
        
    context = {
        'agent': agent,
        'form': form,
        'credentials': agent.credentials.all().order_by('order'),
        'section': 'profile'
    }
    return render(request, 'core/manage_profile.html', context)


@login_required
def manage_bespoke_profile(request, agent):
    """
    VIP Dashboard logic. Automatically absorbs any HTML form inputs 
    and saves them directly into the agent's bespoke JSON field.
    """
    if request.method == 'POST':
        # Grab the existing JSON data so we don't accidentally wipe it
        custom_data = agent.bespoke_data or {}

        # Loop through every input field submitted in the HTML form
        for key, value in request.POST.items():
            # Ignore standard Django hidden security fields
            if key not in ['csrfmiddlewaretoken']:
                custom_data[key] = value.strip()

        # Save the updated JSON dictionary back to the database
        agent.bespoke_data = custom_data
        agent.save()
        
        messages.success(request, "Your VIP profile has been updated.")
        return redirect('manage_profile')

    # Send her existing JSON data to her custom dashboard template
    context = {
        'agent': agent,
        'custom_fields': agent.bespoke_data or {},
        'section': 'profile' # Keeps the sidebar highlighted correctly
    }
    
    # You will create this specific HTML file for her dashboard edits
    return render(request, 'core/manage_bespoke_profile.html', context)

def domain_expertise(request):
    host = request.get_host().split(':')[0].lower()
    subdomain = host.split('.')[0]
    return agent_bio(request, slug=subdomain)

def domain_letters(request):
    host = request.get_host().split(':')[0].lower()
    subdomain = host.split('.')[0]
    return agent_testimonials(request, slug=subdomain)

def send_telegram_notification(bot_token, chat_id, message):
    """Hits the Telegram API to send an instant push notification."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML" # Allows us to use bolding and clean formatting
    }
    try:
        # We use a timeout so if Telegram's API is slow, it doesn't freeze your website
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram notification failed: {e}")

@csrf_exempt  # Telegram's servers don't have our CSRF token, so we must exempt this route
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            message = payload.get('message', {})
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')

            # Check if this is a deep-link start command from the dashboard
            if text.startswith('/start agent_'):
                # Extract the username from the command (e.g., "lakshan" from "/start agent_lakshan")
                username = text.split('agent_')[1].strip()
                
                # Find the agent in the database
                user = User.objects.filter(username=username).first()
                if user and hasattr(user, 'agent'):
                    agent = user.agent
                    
                    # Save the ID!
                    agent.telegram_chat_id = str(chat_id)
                    agent.save()

                    # Send a success confirmation back to the agent's phone
                    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" # Replace with your token
                    success_msg = f"✅ <b>Success!</b>\n\nYour Skandage account (<b>{agent.name}</b>) is now connected.\n\nYou will receive instant notifications here whenever a new lead submits your form."
                    send_telegram_notification(BOT_TOKEN, chat_id, success_msg)

        except Exception as e:
            print(f"Webhook processing error: {e}")

    # You must always return a 200 OK so Telegram knows you received it
    return HttpResponse('OK')