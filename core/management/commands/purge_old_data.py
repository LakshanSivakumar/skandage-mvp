import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Subscriber

class Command(BaseCommand):
    help = 'Anonymizes soft-deleted client records older than 7 years (PDPA Compliance).'

    def handle(self, *args, **kwargs):
        # Calculate the cutoff date (7 years ago)
        # Using 365.25 days to account for leap years
        cutoff_date = timezone.now() - timedelta(days=365.25 * 7)
        
        # Find records that are archived, not yet anonymized, and older than the cutoff
        records_to_purge = Subscriber.objects.filter(
            is_active=False,
            is_anonymized=False,
            archived_at__lte=cutoff_date
        )
        
        count = records_to_purge.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No records require purging today."))
            return

        for sub in records_to_purge:
            # 1. Mathematically destroy the encrypted payloads
            sub.encrypted_name = b''
            sub.encrypted_email = b''
            sub.encrypted_phone = b''
            sub.encrypted_address = b''
            sub.encrypted_dob = b''
            sub.encrypted_notes = b''
            
            # 2. Randomize the hashes to break any database linking
            sub.email_hash = f"scrubbed_{uuid.uuid4().hex}"
            sub.name_hash = f"scrubbed_{uuid.uuid4().hex}"
            
            # 3. Mark as complete
            sub.is_anonymized = True
            sub.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully anonymized {count} expired records."))