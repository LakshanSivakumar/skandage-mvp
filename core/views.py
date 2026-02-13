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

# ==========================
# VCARD DOWNLOAD VIEW
# ==========================
def download_vcard(request, slug):
    agent = get_object_or_404(Agent, slug=slug, is_public=True)
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
            return redirect('agent_profile', slug=slug)
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
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        agent = Agent.objects.create(user=request.user, name=request.user.username)

    leads = Lead.objects.filter(agent=agent).order_by('-created_at')
    
    context = {
        'agent': agent,
        'leads': leads,
        'section': 'stats'
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
    # Try to find an agency owned by this user
    try:
        agency = Agency.objects.get(owner=request.user)
    except Agency.DoesNotExist:
        # If no agency exists for this user, create a placeholder or redirect
        # For now, let's create a placeholder
        agency = Agency.objects.create(
            owner=request.user, 
            domain="yq-partners.com", 
            name="YQ Partners"
        )

    if request.method == 'POST':
        form = AgencySiteForm(request.POST, request.FILES, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, "Agency website updated successfully!")
            return redirect('manage_agency_site')
    else:
        form = AgencySiteForm(instance=agency)

    return render(request, 'core/manage_agency.html', {'form': form, 'agency': agency, 'image_form': AgencyImageForm(),'review_form': AgencyReviewForm()} )

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