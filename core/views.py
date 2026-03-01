import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib import messages
from django.urls import reverse
from .models import Agent, Testimonial, Lead, Article, Credential, Service, ReviewLink, Agency, AgencyImage, AgencyReview
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
from .models import Subscriber, Newsletter
from django.core.mail import get_connection, EmailMultiAlternatives
from django.utils.html import strip_tags
from .models import hash_email
from django.template.loader import render_to_string
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
                from_email=f"{agent.name} <updates@skandage.com>",
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
        form = ClientSubmissionForm(request.POST)
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

    context = {
        'agent': agent,
        'agency': agency, 
        'leads': leads,
        'section': 'stats',
        # Pass new variables to the template:
        'audience_size': audience_size,
        'broadcasts_sent': broadcasts_sent,
        'conversion_rate': conversion_rate,
    }
    return render(request, 'core/dashboard_stats.html', context)

@login_required
def manage_profile(request):
    agent = request.user.agent
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
    agent = get_object_or_404(Agent, slug=slug, is_public=True) # Check Public
    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    testimonials = agent.testimonials.filter(is_published=True).order_by('-is_featured', '-id')
    return render(request, 'core/public_testimonials.html', {
        'agent': agent,
        'testimonials': testimonials,
        'theme': theme_config
    })

def agent_bio(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True) # Check Public
    theme_config = THEMES.get(agent.theme, THEMES['luxe'])
    return render(request, 'core/public_bio.html', {
        'agent': agent,
        'credentials': agent.credentials.all().order_by('order'),
        'theme': theme_config
    })

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
    
    # Handle Manual Add
    if request.method == 'POST' and 'add_subscriber' in request.POST:
        name = request.POST.get('name')
        raw_email = request.POST.get('email')
        hashed = hash_email(raw_email)
        
        if Subscriber.objects.filter(agent=agent, email_hash=hashed).exists():
            messages.warning(request, f"Skipped: That client is already in your vault.")
        else:
            sub = Subscriber(agent=agent, name=name, source='manual')
            sub.email = raw_email # Encrypts it
            sub.save()
            messages.success(request, f"Securely vaulted new client.")
        return redirect('manage_subscribers')

    # Handle CSV Import
    if request.method == 'POST' and 'import_csv' in request.POST:
        csv_file = request.FILES.get('csv_file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid .csv file.")
            return redirect('manage_subscribers')

        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=',')
        next(reader, None) 

        added = 0
        skipped_emails = []
        
        for row in reader:
            if len(row) >= 2:
                name = row[0].strip()
                raw_email = row[1].strip()
                
                if raw_email:
                    hashed = hash_email(raw_email)
                    if not Subscriber.objects.filter(agent=agent, email_hash=hashed).exists():
                        sub = Subscriber(agent=agent, name=name, source='csv_import')
                        sub.email = raw_email # Encrypts it
                        sub.save()
                        added += 1
                    else:
                        skipped_emails.append(raw_email)
        
        if added > 0:
            messages.success(request, f"Successfully vaulted {added} new clients!")
        if skipped_emails:
            skipped_str = ", ".join(skipped_emails[:5]) 
            more = f" and {len(skipped_emails) - 5} more" if len(skipped_emails) > 5 else ""
            messages.warning(request, f"Skipped duplicates: {skipped_str}{more}.")
            
        return redirect('manage_subscribers')

    subscribers = agent.subscribers.all().order_by('-created_at')
    return render(request, 'core/manage_subscribers.html', {'agent': agent, 'subscribers': subscribers, 'section': 'audience'})

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