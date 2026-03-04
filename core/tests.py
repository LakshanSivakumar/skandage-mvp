from django.test import TestCase
from django.contrib.auth.models import User
from .models import Agent, Subscriber, CardTemplate, CardLog
from .services import get_best_card_for_subscriber
from datetime import date, timedelta

class CardEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testagent', password='password')
        self.agent = Agent.objects.create(user=self.user, name="Test Agent")
        
        # Create Subscribers
        # Note: We instantiate and save manually because 'email' is a property that handles encryption,
        # so passing it directly to objects.create() would cause an error.
        self.sub_male_30 = Subscriber(
            agent=self.agent, name="John Doe",
            gender='M', date_of_birth=date.today() - timedelta(days=365*30)
        )
        self.sub_male_30.email = "john@example.com"
        self.sub_male_30.save()

        self.sub_female_25 = Subscriber(
            agent=self.agent, name="Jane Doe",
            gender='F', date_of_birth=date.today() - timedelta(days=365*25)
        )
        self.sub_female_25.email = "jane@example.com"
        self.sub_female_25.save()

        self.sub_unknown = Subscriber(
            agent=self.agent, name="Alex",
            gender='U', date_of_birth=None
        )
        self.sub_unknown.email = "alex@example.com"
        self.sub_unknown.save()

        # Create Templates
        self.card_generic = CardTemplate.objects.create(
            agent=self.agent, name="Generic Birthday", occasion="Birthday",
            target_gender='A', target_age_min=0, target_age_max=120
        )
        self.card_male_only = CardTemplate.objects.create(
            agent=self.agent, name="Male Birthday", occasion="Birthday",
            target_gender='M', target_age_min=0, target_age_max=120
        )
        self.card_young_female = CardTemplate.objects.create(
            agent=self.agent, name="Young Female Birthday", occasion="Birthday",
            target_gender='F', target_age_min=18, target_age_max=29
        )

    def test_card_log_creation(self):
        """Test that CardLog can be created and enforces unique constraint."""
        log = CardLog.objects.create(
            agent=self.agent,
            subscriber=self.sub_male_30,
            card_template=self.card_generic,
            occasion="Birthday",
            scheduled_date=date.today()
        )
        self.assertEqual(log.status, 'pending')
        
        # Test unique constraint (cannot log same occasion for same person on same day)
        from django.db.utils import IntegrityError
        with self.assertRaises(IntegrityError):
            CardLog.objects.create(
                agent=self.agent,
                subscriber=self.sub_male_30,
                card_template=self.card_generic,
                occasion="Birthday",
                scheduled_date=date.today()
            )

    def test_matchmaker_male(self):
        """Male subscriber should prefer Male card over Generic."""
        best_card = get_best_card_for_subscriber(self.agent, self.sub_male_30, "Birthday")
        self.assertEqual(best_card, self.card_male_only)

    def test_matchmaker_female_age_match(self):
        """Female 25 should match Young Female card."""
        best_card = get_best_card_for_subscriber(self.agent, self.sub_female_25, "Birthday")
        self.assertEqual(best_card, self.card_young_female)

    def test_matchmaker_unknown_demographics(self):
        """Subscriber with no DOB/Gender should only match Generic."""
        best_card = get_best_card_for_subscriber(self.agent, self.sub_unknown, "Birthday")
        self.assertEqual(best_card, self.card_generic)

    def test_matchmaker_occasion_mismatch(self):
        """Should not return Birthday card for Christmas."""
        best_card = get_best_card_for_subscriber(self.agent, self.sub_male_30, "Christmas")
        self.assertIsNone(best_card)
