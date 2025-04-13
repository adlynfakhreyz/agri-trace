from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
import json

from authentication.models import Farmer
from farm.models import Farm, Field, Crop, ActivityLog

User = get_user_model()

class MainViewsTests(TestCase):

    def setUp(self):
        """Setup data untuk tests."""
        self.client = Client()
        self.password = 'aSecurePassword123!'
        self.user_farmer = User.objects.create_user(
            username='mainfarmer',
            password=self.password,
            email='farmer@example.com'
        )
        self.farmer_profile = Farmer.objects.create(user=self.user_farmer)
        self.user_no_profile = User.objects.create_user(
            username='nofarmer',
            password=self.password,
            email='nofarmer@example.com'
        )

        self.farm = Farm.objects.create(farmer=self.farmer_profile, name="Main Test Farm", size=10)
        self.field = Field.objects.create(farm=self.farm, name="Main Field", size=5)
        self.crop = Crop.objects.create(field=self.field, crop_type="Test Crop", planting_date=timezone.now().date())
        self.activity = ActivityLog.objects.create(farm=self.farm, activity_type='maintenance', timestamp=timezone.now())

        self.home_url = reverse('home')
        self.dashboard_url = reverse('dashboard')
        self.about_us_url = reverse('about_us')
        self.contact_url = reverse('contact')
        self.toggle_drawer_url = reverse('toggle_drawer')
        self.login_url = reverse('login')

    # === Test Views Publik ===
    def test_home_view(self):
        """Test home view renders correctly."""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_about_us_view(self):
        """Test about_us view renders correctly."""
        response = self.client.get(self.about_us_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about_us.html')

    def test_contact_view(self):
        """Test contact view renders correctly."""
        response = self.client.get(self.contact_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')

    # === Test Dashboard View ===
    def test_dashboard_view_unauthenticated(self):
        """Test dashboard redirects to login if user not authenticated."""
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.dashboard_url}')

    def test_dashboard_view_no_farmer_profile(self):
        """Test dashboard for logged-in user without farmer profile."""
        self.client.login(username=self.user_no_profile.username, password=self.password)
        response = self.client.get(self.dashboard_url)

        # Check profile created and warning message shown
        self.assertTrue(Farmer.objects.filter(user=self.user_no_profile).exists())
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "You need to set up a farmer profile first.")

        # Check context for no farms scenario
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertEqual(response.context['farm_count'], 0)
        self.assertFalse(response.context['has_farms'])

        self.client.logout() # Logout user_no_profile

    def test_dashboard_view_farmer_no_farms(self):
        """Test dashboard for farmer user with no farms."""
        # Create a new farmer user specifically for this test
        user_farmer_no_farm = User.objects.create_user(username='emptyfarmer', password=self.password)
        Farmer.objects.create(user=user_farmer_no_farm)

        self.client.login(username='emptyfarmer', password=self.password)
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertEqual(response.context['farm_count'], 0)
        self.assertFalse(response.context['has_farms'])

        self.client.logout() # Logout emptyfarmer

    def test_dashboard_view_farmer_with_farms(self):
        """Test dashboard for farmer user with farms and data."""
        self.client.login(username=self.user_farmer.username, password=self.password)
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertTrue(response.context['has_farms'])
        self.assertEqual(response.context['farm_count'], 1)
        self.assertEqual(len(response.context['farms']), 1)
        self.assertEqual(response.context['farms'][0], self.farm)
        self.assertEqual(response.context['total_crops'], 1) # Based on setUp data
        self.assertEqual(len(response.context['recent_activities']), 1)
        self.assertEqual(response.context['recent_activities'][0], self.activity)

        # Check if farm name and activity type appear in rendered HTML
        self.assertContains(response, self.farm.name)
        self.assertContains(response, self.activity.get_activity_type_display())

        self.client.logout() # Logout user_farmer

    # === Test Toggle Drawer View ===
    def test_toggle_drawer_unauthenticated(self):
        """Test toggle_drawer redirects to login if user not authenticated."""
        response = self.client.post(self.toggle_drawer_url, {'collapsed': 'true'})
        self.assertRedirects(response, f'{self.login_url}?next={self.toggle_drawer_url}')

    def test_toggle_drawer_get_not_allowed(self):
        """Test GET request to toggle_drawer returns 400."""
        self.client.login(username=self.user_farmer.username, password=self.password)
        response = self.client.get(self.toggle_drawer_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Only POST method is allowed')
        self.client.logout()

    def test_toggle_drawer_post_set_true(self):
        """Test POST request sets session drawer_collapsed to True."""
        self.client.login(username=self.user_farmer.username, password=self.password)
        # Ensure session is initially different or non-existent
        session = self.client.session
        session['drawer_collapsed'] = False
        session.save()

        response = self.client.post(self.toggle_drawer_url, {'collapsed': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Check session value updated
        self.assertTrue(self.client.session.get('drawer_collapsed'))
        self.client.logout()

    def test_toggle_drawer_post_set_false(self):
        """Test POST request sets session drawer_collapsed to False."""
        self.client.login(username=self.user_farmer.username, password=self.password)
        # Ensure session is initially different or non-existent
        session = self.client.session
        session['drawer_collapsed'] = True
        session.save()

        response = self.client.post(self.toggle_drawer_url, {'collapsed': 'false'}) # Any value other than 'true' becomes False
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        data = response.json()
        self.assertEqual(data['status'], 'success')

        # Check session value updated
        self.assertFalse(self.client.session.get('drawer_collapsed'))
        self.client.logout()