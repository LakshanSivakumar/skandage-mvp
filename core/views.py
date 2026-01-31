from django.shortcuts import render, get_object_or_404
from .models import Agent, Testimonial, Lead
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .forms import AgentProfileForm, TestimonialForm, LeadForm # <--- Import LeadForm

def agent_profile(request, slug):
    agent = get_object_or_404(Agent, slug=slug)
    
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.agent = agent
            lead.save()
            print("--- SUCCESS: Lead Saved! ---") # Debug Success
            return redirect('agent_profile', slug=slug)
        else:
            print("--- FORM FAILED: ", form.errors) # <--- THIS IS WHAT WE NEED
    else:
        form = LeadForm()

    context = {
        'agent': agent,
        'testimonials': agent.testimonials.all(),
        'services': agent.services.all(),
        'credentials': agent.credentials.all(), # Ensure this is passed if you use it
        'form': form,
    }
    return render(request, 'core/agent_profile.html', context)

@login_required
def dashboard(request):
    # 1. Get or Create the Agent Profile
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        agent = Agent.objects.create(user=request.user, name=request.user.username)
    
    # 2. Always fetch leads (Now that we know agent exists)
    # We do this OUTSIDE the try/except so it runs for everyone
    leads = Lead.objects.filter(agent=agent).order_by('-created_at')

    # 3. Handle the Form
    if request.method == 'POST':
        form = AgentProfileForm(request.POST, request.FILES, instance=agent)
        if form.is_valid():
            form.save()
            return redirect('dashboard') 
    else:
        form = AgentProfileForm(instance=agent)
    
    # 4. Prepare Context (Combine everything)
    context = {
        'form': form,
        'agent': agent,   # <--- Required for sidebar/stats
        'leads': leads,   # <--- Required for the Inbox
    }

    # 5. Render
    return render(request, 'core/dashboard.html', context)

@login_required
def add_testimonial(request):
    # Ensure user has an agent profile
    agent = request.user.agent
    
    if request.method == 'POST':
        form = TestimonialForm(request.POST, request.FILES)
        if form.is_valid():
            testimonial = form.save(commit=False)
            testimonial.agent = agent  # Link it to the logged-in agent
            testimonial.save()
            return redirect('dashboard')
    else:
        form = TestimonialForm()

    return render(request, 'core/add_testimonial.html', {'form': form})

@login_required
def delete_testimonial(request, pk):
    # Get the testimonial, but ONLY if it belongs to the logged-in user's agent
    # This prevents users from deleting each other's data (Security!)
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=request.user.agent)
    
    if request.method == 'POST':
        testimonial.delete()
        return redirect('dashboard')
        
    return render(request, 'core/delete_confirm.html', {'testimonial': testimonial})

@login_required
def edit_testimonial(request, pk):
    # Get the specific testimonial, ensuring it belongs to the logged-in user
    testimonial = get_object_or_404(Testimonial, pk=pk, agent=request.user.agent)
    
    if request.method == 'POST':
        # 'instance=testimonial' tells Django to update this specific one, not create new
        form = TestimonialForm(request.POST, request.FILES, instance=testimonial)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        # Pre-fill the form with current data
        form = TestimonialForm(instance=testimonial)

    return render(request, 'core/edit_testimonial.html', {'form': form, 'testimonial': testimonial})
@login_required
def edit_bio(request):
    agent = request.user.agent
    if request.method == 'POST':
        # We manually update just the bio field
        agent.bio = request.POST.get('bio')
        agent.save()
        return redirect('dashboard')
    return render(request, 'core/edit_bio.html', {'agent': agent})

@login_required
def upload_headshot(request):
    agent = request.user.agent
    if request.method == 'POST':
        # We manually handle the file upload
        if 'headshot' in request.FILES:
            agent.headshot = request.FILES['headshot']
            agent.save()
        return redirect('dashboard')
    return render(request, 'core/upload_headshot.html', {'agent': agent})

def domain_router(request):
    """
    The Traffic Controller:
    1. Checks the domain name (e.g., 'benedict.skandage.com')
    2. Extracts the subdomain ('benedict')
    3. Serves the correct Agent Profile
    """
    host = request.get_host().split(':')[0] # Remove port number if present
    
    # List of "Reserved" subdomains that should act like the main site
    reserved_domains = ['www', 'skandage', 'app', 'localhost', '127.0.0.1']
    
    # Get the subdomain (e.g., "benedict" from "benedict.skandage.com")
    subdomain = host.split('.')[0]

    if subdomain in reserved_domains:
        # If it's the main site, show the Landing Page (or Login)
        return render(request, 'core/index.html') # You need an index.html, or redirect to login
    
    else:
        # It's an AGENT! Load their profile using the subdomain as the slug
        return agent_profile(request, slug=subdomain)