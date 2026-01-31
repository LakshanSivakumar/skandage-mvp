from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .models import Agent, Testimonial, Lead, Article, Credential
from .forms import AgentProfileForm, TestimonialForm, LeadForm, ArticleForm, CredentialForm, UserUpdateForm

# ==========================================
# PUBLIC VIEWS (Accessible by Everyone)
# ==========================================

def domain_router(request):
    """
    The Traffic Controller:
    Checks if the request is for a subdomain (e.g., benedict.skandage.com)
    and routes it to the correct agent profile.
    """
    host = request.get_host().split(':')[0] # Remove port number
    reserved_domains = ['www', 'skandage', 'app', 'localhost', '127.0.0.1']
    subdomain = host.split('.')[0]

    if subdomain in reserved_domains:
        # If it's the main site, show the Landing Page (or redirect to Login)
        return render(request, 'core/index.html') 
    else:
        # It's an AGENT! Load their profile using the subdomain as the slug
        return agent_profile(request, slug=subdomain)

def agent_profile(request, slug):
    agent = get_object_or_404(Agent, slug=slug)
    
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
        'testimonials': agent.testimonials.all(),
        'services': agent.services.all(),
        'credentials': agent.credentials.all(),
        'articles': agent.articles.all().order_by('-created_at'),
        'form': form,
    }
    return render(request, 'core/agent_profile.html', context)

def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'core/article_detail.html', {'article': article, 'agent': article.agent})


# ==========================================
# DASHBOARD VIEWS (Protected Area)
# ==========================================

@login_required
def dashboard_stats(request):
    """
    The Main Dashboard Page: Shows Stats & Leads
    """
    # Ensure Agent Profile Exists
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        agent = Agent.objects.create(user=request.user, name=request.user.username)

    leads = Lead.objects.filter(agent=agent).order_by('-created_at')
    
    context = {
        'agent': agent,
        'leads': leads,
        'section': 'stats' # Highlights sidebar
    }
    return render(request, 'core/dashboard_stats.html', context)

@login_required
def manage_profile(request):
    """
    Edit Profile Details, Bio, Headshot & Credentials
    """
    agent = request.user.agent
    
    if request.method == 'POST':
        # Handle the Profile Form (Bio, Name, Headshot, etc.)
        form = AgentProfileForm(request.POST, request.FILES, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('manage_profile')
    else:
        form = AgentProfileForm(instance=agent)

    context = {
        'agent': agent,
        'form': form,
        'credentials': agent.credentials.all(),
        'section': 'profile'
    }
    return render(request, 'core/manage_profile.html', context)

@login_required
def manage_articles(request):
    """
    List all articles with Edit/Delete options
    """
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
    """
    List all testimonials with Edit/Delete options
    """
    agent = request.user.agent
    testimonials = agent.testimonials.all()
    
    context = {
        'agent': agent,
        'testimonials': testimonials,
        'section': 'testimonials'
    }
    return render(request, 'core/manage_testimonials.html', context)


# ==========================================
# ACTION VIEWS (Create, Edit, Delete)
# ==========================================

# --- ARTICLES ---
@login_required
def create_article(request):
    agent = request.user.agent
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.agent = agent
            article.save()
            return redirect('manage_articles') # Redirect back to list
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

# --- CREDENTIALS ---
@login_required
def add_credential(request):
    agent = request.user.agent
    
    if request.method == 'POST':
        form = CredentialForm(request.POST)
        if form.is_valid():
            cred = form.save(commit=False)
            cred.agent = agent
            cred.save()
            return redirect('manage_profile')
    else:
        # This was missing! We need to create an empty form for GET requests
        form = CredentialForm() 
    
    return render(request, 'core/generic_form.html', {'form': form, 'title': 'Add New Credential'})

@login_required
def delete_credential(request, pk):
    cred = get_object_or_404(Credential, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        cred.delete()
    return redirect('manage_profile')

# --- TESTIMONIALS ---
@login_required
def add_testimonial(request):
    agent = request.user.agent
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.agent = agent
            testimonial.save()
            return redirect('manage_testimonials')
    else:
        form = TestimonialForm()

    return render(request, 'core/add_testimonial.html', {'form': form})

@login_required
def edit_testimonial(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            form.save()
            return redirect('manage_testimonials')
    else:
        form = TestimonialForm(instance=testimonial)

    return render(request, 'core/edit_testimonial.html', {'form': form, 'testimonial': testimonial})

@login_required
def delete_testimonial(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=request.user.agent)
    if request.method == 'POST':
        testimonial.delete()
        return redirect('manage_testimonials')
        
    return render(request, 'core/delete_confirm.html', {'testimonial': testimonial})

# Note: edit_bio and upload_headshot have been removed as they are now handled in manage_profile

@login_required
def delete_lead(request, pk):
    # Ensure the lead belongs to the logged-in agent (Security)
    lead = get_object_or_404(Lead, pk=pk, agent=request.user.agent)
    
    if request.method == 'POST':
        lead.delete()
        return redirect('dashboard')
    
    # If someone tries GET, just redirect them back
    return redirect('dashboard')

# --- NEW VIEW: ACCOUNT SETTINGS ---
@login_required
def account_settings(request):
    user = request.user
    
    if request.method == 'POST':
        # Check which form was submitted based on the button name
        if 'update_profile' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=user)
            password_form = PasswordChangeForm(user) # Empty form
            
            if user_form.is_valid():
                user_form.save()
                return redirect('account_settings')
                
        elif 'change_password' in request.POST:
            user_form = UserUpdateForm(instance=user) # Keep existing data
            password_form = PasswordChangeForm(user, request.POST)
            
            if password_form.is_valid():
                user = password_form.save()
                # Important! Updating password logs you out unless you do this:
                update_session_auth_hash(request, user) 
                return redirect('account_settings')
    else:
        user_form = UserUpdateForm(instance=user)
        password_form = PasswordChangeForm(user)

    context = {
        'user_form': user_form,
        'password_form': password_form,
        'section': 'settings' # For sidebar highlighting
    }
    return render(request, 'core/account_settings.html', context)