from datetime import date
from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db.models import Q
from core.models import Agent, Subscriber, CardTemplate, CardLog

class Command(BaseCommand):
    help = 'Processes daily birthday cards based on Agent auto/manual preferences.'

    def handle(self, *args, **kwargs):
        today = date.today()
        agents = Agent.objects.filter(is_public=True)
        
        for agent in agents:
            birthdays = Subscriber.objects.filter(
                agent=agent, is_active=True,
                date_of_birth__month=today.month, date_of_birth__day=today.day
            )

            if not birthdays.exists():
                continue

            pending_count = 0

            for sub in birthdays:
                # Deduplication logic
                if CardLog.objects.filter(agent=agent, subscriber=sub, occasion='Birthday', scheduled_date=today).exists():
                    continue

                age = today.year - sub.date_of_birth.year
                
                # Exact demographic match
                template = CardTemplate.objects.filter(
                    agent=agent, occasion='Birthday', is_active=True
                ).filter(Q(target_gender='A') | Q(target_gender=sub.gender)
                ).filter(target_age_min__lte=age, target_age_max__gte=age).first()

                if not template:
                    continue

                # --- AUTO SEND MODE ---
                if agent.automation_mode == 'auto':
                    if sub.email:
                        subject = f"Happy Birthday, {sub.name}!"
                        # 1. Get the base site URL (Make sure SITE_URL is set in your production settings.py!)
                        site_url = getattr(settings, 'SITE_URL', 'https://skandage.com').rstrip('/')

                        # 2. Smart URL Builder for the Card Image
                        card_image_url = ""
                        if template and template.image:
                            card_image_url = template.image.url
                            # If using local storage, prepend the domain. If using S3, it already has 'http'
                            if not card_image_url.startswith('http'):
                                card_image_url = f"{site_url}{card_image_url}"

                        # 3. Smart URL Builder for the Agent Headshot
                        agent_headshot_url = ""
                        if agent.headshot:
                            agent_headshot_url = agent.headshot.url
                            if not agent_headshot_url.startswith('http'):
                                agent_headshot_url = f"{site_url}{agent_headshot_url}"

                        # 4. Pass them to the template
                        context = {
                            'client_name': sub.name,
                            'agent': agent,
                            'occasion': getattr(log, 'occasion', 'Birthday'), # Handles both view and cron job
                            'message': template.default_message,
                            'card_image_url': card_image_url,
                            'agent_headshot_url': agent_headshot_url,
                            'occasion_emoji': '🎂'
}
                        
                        html_content = render_to_string('core/emails/card_email.html', context)
                        text_content = strip_tags(html_content)
                        
                        msg = EmailMultiAlternatives(subject=subject, body=text_content, from_email=f"{agent.name} <updates@skandage.com>", to=[sub.email])
                        msg.attach_alternative(html_content, "text/html")
                        
                        try:
                            msg.send(fail_silently=False)
                            CardLog.objects.create(agent=agent, subscriber=sub, card_template=template, occasion='Birthday', status='sent', scheduled_date=today, sent_at=timezone.now())
                            self.stdout.write(self.style.SUCCESS(f"Auto-sent birthday card to {sub.name} for {agent.name}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Failed to auto-send to {sub.name}: {e}"))
                            CardLog.objects.create(agent=agent, subscriber=sub, card_template=template, occasion='Birthday', status='failed', scheduled_date=today, error_message=str(e))
                
                # --- MANUAL APPROVAL MODE ---
                else:
                    if sub.email:
                        pending_count += 1
                        CardLog.objects.create(agent=agent, subscriber=sub, card_template=template, occasion='Birthday', status='pending', scheduled_date=today)

            # DISPATCH DIGEST EMAIL
            if agent.automation_mode == 'manual' and pending_count > 0:
                target_email = agent.notification_email if agent.notification_email else (agent.user.email if agent.user else None)
                
                if target_email:
                    send_mail(
                        subject=f"Action Required: {pending_count} Client Birthdays Today",
                        message=f"Good morning {agent.name},\n\nYou have {pending_count} client birthdays today. Please log in to your Skandage dashboard to review and send their cards:\n\nhttps://app.skandage.com/dashboard/crm/pending/",
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'updates@skandage.com'),
                        recipient_list=[target_email],
                        fail_silently=True,
                    )
                    self.stdout.write(self.style.NOTICE(f"Sent manual digest to {agent.name} at {target_email}"))

        self.stdout.write(self.style.SUCCESS("Daily card processing complete."))