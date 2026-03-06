from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Agent, Subscriber
from core.festivals import FESTIVALS_2026
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class Command(BaseCommand):
    help = 'Sends a consolidated daily email summary of CRM events (Birthdays, Reviews, Festivals) to all active agents.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        today_str = today.strftime('%Y-%m-%d')
        
        # Determine if today is a festival
        today_festivals = [name for name, date in FESTIVALS_2026.items() if date == today_str]
        
        agents = Agent.objects.filter(is_public=True)
        emails_sent = 0

        for agent in agents:
            # Check if agent has a notification email setup, else fallback to their login user email
            recipient_email = getattr(agent, 'notification_email', None)
            if not recipient_email and agent.user:
                recipient_email = agent.user.email
                
            if not recipient_email:
                self.stdout.write(self.style.WARNING(f"Agent {agent.name} has no email configured. Skipping."))
                continue

            subscribers = agent.subscribers.filter(is_active=True)
            
            birthdays_today = []
            reviews_today = []
            festive_today = []

            for sub in subscribers:
                # 1. Check Birthdays
                if sub.birth_month == today.month and sub.birth_day == today.day:
                    birthdays_today.append(sub)
                
                # 2. Check Reviews
                if sub.next_review_date == today:
                    reviews_today.append(sub)
                
                # 3. Check Festivals (compare sub.tag_list with today_festivals)
                if today_festivals:
                    sub_tags = sub.tag_list
                    matched_fests = [f for f in today_festivals if f in sub_tags]
                    if matched_fests:
                        festive_today.append({'subscriber': sub, 'festivals': matched_fests})

            # If there's an event for exactly this agent today, send the consolidated email
            if birthdays_today or reviews_today or festive_today:
                
                context = {
                    'agent': agent,
                    'date': today,
                    'birthdays': birthdays_today,
                    'reviews': reviews_today,
                    'festivals': festive_today,
                    'domain': agent.agency_site.domain if hasattr(agent, 'agency_site') and agent.agency_site else getattr(settings, 'SITE_URL', 'https://skandage.com')
                }

                html_message = render_to_string('core/emails/daily_crm_reminder.html', context)
                plain_message = strip_tags(html_message)
                subject = f"🔔 Your Daily Skandage CRM Summary ({today.strftime('%d %b %Y')})"
                
                try:
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient_email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    emails_sent += 1
                    self.stdout.write(self.style.SUCCESS(f"Sent summary email to {agent.name} ({recipient_email})"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Failed to send email to {agent.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully finished sending {emails_sent} CRM daily reminder emails."))
