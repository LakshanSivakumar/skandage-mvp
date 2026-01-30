from django.shortcuts import render, get_object_or_404
from .models import Agent, Testimonial
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .forms import AgentProfileForm, TestimonialForm

def agent_profile(request, slug):
    # This tries to find the agent. If they don't exist, it shows a 404 error.
    agent = get_object_or_404(Agent, slug=slug)
    print(f"DEBUG: Agent is {agent.name}, Tagline is: '{agent.tagline}'")
    print(f"--- PUBLIC SITE VIEWING: Agent ID {agent.id} | Slug: {agent.slug} | Tagline: {agent.tagline}")
    context = {
        'agent': agent,
        'testimonials': agent.testimonials.all(),
        'services': agent.services.all(),
    }
    return render(request, 'core/agent_profile.html', context)

@login_required
def dashboard(request):
    # 1. Get or Create the Agent Profile
    try:
        agent = request.user.agent
    except Agent.DoesNotExist:
        agent = Agent.objects.create(user=request.user, name=request.user.username)

    # 2. Handle the "Save" Action (POST)
    if request.method == 'POST':
        # We bind the form to the POST data and the existing agent instance
        form = AgentProfileForm(request.POST, request.FILES, instance=agent)
        
        if form.is_valid():
            form.save()
            return redirect('dashboard') # Success! Reload page.
        else:
            # If errors, we fall through to render the page with the error messages
            pass 
            
    # 3. Handle the "View" Action (GET)
    else:
        # Pre-fill the form with the current database values
        form = AgentProfileForm(instance=agent)
    
    # 4. Render the Template
    return render(request, 'core/dashboard.html', {'form': form})

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