import requests
from django.core.management.base import BaseCommand
from core.models import Agent

class Command(BaseCommand):
    help = 'Pings AIA API and updates bespoke_data for VIP agents'

    def format_currency(self, value):
        if not value: return "SGD 0"
        if value >= 1000000:
            return f"SGD {value/1000000:.1f} m"
        elif value >= 1000:
            return f"SGD {value/1000:.1f} k"
        return f"SGD {value}"

    def handle(self, *args, **kwargs):
        # We will target Karna's profile (make sure 'karna' is her actual slug)
        try:
            agent = Agent.objects.get(slug='karna')
        except Agent.DoesNotExist:
            self.stdout.write(self.style.ERROR("Agent 'karna' not found."))
            return

        api_url = 'https://mypageapp.aia.com.sg/eprofile/getAgentEProfile'
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'origin': 'https://www.aia.com.sg',
            'referer': 'https://www.aia.com.sg/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        # Replace this fscCode with Karna's actual code when you get her link
        payload = {
            "companyCode": "011",
            "fscCode": "\\xc30d0409030228c10116c67abe5560d23e01d8e9f9204ca0487ffa82ca2d4d10bee8f1c735197511da2a9a9aff8dea8e17909dadc20cdddd15e23e0230c870181b2ac776018407b8eff630cebf1d41"
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Safely get existing bespoke data so we don't overwrite her headlines
            custom_data = agent.bespoke_data or {}
            
            # Inject ALL the clean metrics into a new 'aia_metrics' dictionary
            custom_data['aia_metrics'] = {
                'total_clients': data.get('agtTotPolOwCnt', 0),
                'total_policies': data.get('agtTotPolCnt', 0),
                'claims_approved': data.get('totClmCnt', 0),
                'claims_value': self.format_currency(data.get('totClmAmt')),
                'sum_assured_death': self.format_currency(data.get('totSumAssuredDth')),
                'sum_assured_tpd': self.format_currency(data.get('totSumAssuredPermDisability')),
                'sum_assured_ci': self.format_currency(data.get('totSumAssuredCi')),
            }

            agent.bespoke_data = custom_data
            agent.save()

            self.stdout.write(self.style.SUCCESS(f"Successfully updated all 7 live metrics for {agent.name}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to sync data: {e}"))