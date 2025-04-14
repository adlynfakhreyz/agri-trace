from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.utils import timezone
from unittest.mock import patch
import json

# Import models from farm and authentication
from authentication.models import Farmer
from .models import (
    Farm, FarmCondition, Field, Crop, ActivityLog,
    PreparationLog, PlantingLog, MaintenanceLog, HarvestingLog
)
# Import forms from farm
from .forms import (
    FarmForm, FarmConditionForm, FieldForm,
    ActivityLogForm, PreparationLogForm, PlantingLogForm,
    MaintenanceLogForm, HarvestingLogForm
)

User = get_user_model()

# --- Test for Forms ---
class FarmFormsModuleTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testfarmer', password='password')
        self.farmer = Farmer.objects.create(user=self.user)
        self.farm = Farm.objects.create(farmer=self.farmer, name="Test Farm", location="Here", size=10.0)
        self.field1 = Field.objects.create(farm=self.farm, name="Field 1", size=5.0)
        self.field2 = Field.objects.create(farm=self.farm, name="Field 2", size=3.0)
        self.active_crop = Crop.objects.create(
            field=self.field1,
            crop_type="Corn",
            planting_date=timezone.now().date(),
            is_harvested=False
        )
        self.harvested_crop = Crop.objects.create(
            field=self.field2,
            crop_type="Wheat",
            planting_date=timezone.now().date() - timezone.timedelta(days=100),
            is_harvested=True,
            harvest_date=timezone.now().date() - timezone.timedelta(days=10)
        )

    def test_farm_form_valid(self):
        data = {'name': 'My New Farm', 'location': 'Over There', 'size': 15.5}
        form = FarmForm(data=data)
        self.assertTrue(form.is_valid())

    def test_farm_form_invalid(self):
        data = {'name': '', 'location': 'Somewhere', 'size': 'abc'} # Nama kosong, size bukan angka
        form = FarmForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('size', form.errors)

    def test_farm_condition_form_valid(self):
        data = {'soil_ph': 6.5, 'soil_moisture': 45.2, 'rainfall': 120.5, 'max_daily_temp': 30.1, 'day_length': 12.5}
        form = FarmConditionForm(data=data)
        self.assertTrue(form.is_valid())

    def test_field_form_valid(self):
        data = {'name': 'South Field', 'size': 2.5, 'location_within_farm': 'Near the river'}
        form = FieldForm(data=data)
        self.assertTrue(form.is_valid())

    def test_activity_log_form_valid(self):
        data = {'activity_type': 'preparation', 'timestamp': timezone.now()}
        form = ActivityLogForm(data=data)
        self.assertTrue(form.is_valid())

    def test_preparation_log_form_valid_with_farm(self):
        """Test PreparationLogForm is valid and field choices are correct. (Workaround)"""
        data = {'field': self.field1.pk, 'equipment_used': 'Tractor', 'desc': 'Plowing'}
        form = PreparationLogForm(data=data, farm=self.farm)
        self.assertTrue(form.is_valid(), form.errors)
        expected_reprs = sorted([repr(self.field1), repr(self.field2)])
        actual_reprs = sorted([repr(f) for f in form.fields['field'].queryset])
        self.assertListEqual(actual_reprs, expected_reprs)

    def test_planting_log_form_valid_with_farm(self):
        """Test PlantingLogForm is valid and field choices are correct. (Workaround)"""
        data = {
            'field': self.field2.pk,
            'seed_quantity': 10.5,
            'seed_variety': 'XYZ Hybrid',
            'fertilizer_applied': 5.0,
            'crop_type': 'Soybeans',
            'expected_harvest_date': timezone.now().date() + timezone.timedelta(days=120)
        }
        form = PlantingLogForm(data=data, farm=self.farm)
        self.assertTrue(form.is_valid(), form.errors)
        expected_reprs = sorted([repr(self.field1), repr(self.field2)])
        actual_reprs = sorted([repr(f) for f in form.fields['field'].queryset])
        self.assertListEqual(actual_reprs, expected_reprs)

    def test_maintenance_log_form_valid_with_farm(self):
        """Test MaintenanceLogForm valid & crop choices only show active crops. (Workaround)"""
        data = {
            'crop': self.active_crop.pk,
            'pesticide_applied': 1.5,
            'irrigation_amount': 500.0,
            'fertilizer_applied': 2.0
        }
        form = MaintenanceLogForm(data=data, farm=self.farm)
        self.assertTrue(form.is_valid(), form.errors)
        expected_reprs = sorted([repr(self.active_crop)])
        actual_reprs = sorted([repr(c) for c in form.fields['crop'].queryset])
        self.assertListEqual(actual_reprs, expected_reprs)
        self.assertNotIn(repr(self.harvested_crop), actual_reprs)

    def test_harvesting_log_form_valid_with_farm(self):
        """Test HarvestingLogForm valid & crop choices only show active crops."""
        data = {
            'crop': self.active_crop.pk,
            'yield_amount': 1500.0,
            'harvest_quality': 'good'
        }
        form = HarvestingLogForm(data=data, farm=self.farm)
        self.assertTrue(form.is_valid(), form.errors)
        # Check queryset only contains active crops for this farm
        self.assertQuerysetEqual(
            form.fields['crop'].queryset,
            [repr(self.active_crop)],
            transform=repr
        )
        self.assertNotIn(self.harvested_crop, form.fields['crop'].queryset)


# --- Test untuk Views ---
class FarmModuleViewsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.password = 'StrongPass123!'
        # Farmer User
        self.farmer_user = User.objects.create_user(username='farmerjoe', password=self.password, email='joe@farm.com')
        self.farmer_profile = Farmer.objects.create(user=self.farmer_user)
        # Non-Farmer User
        self.other_user = User.objects.create_user(username='cityslicker', password=self.password, email='city@example.com')
        # Another Farmer User (for ownership tests)
        self.other_farmer_user = User.objects.create_user(username='farmerjane', password=self.password, email='jane@farm.com')
        self.other_farmer_profile = Farmer.objects.create(user=self.other_farmer_user)

        # Data for farmer_user
        self.farm1 = Farm.objects.create(farmer=self.farmer_profile, name="Joe's Farm", location="Valley", size=20.0)
        self.farm1_condition = FarmCondition.objects.create(farm=self.farm1, soil_ph=6.8)
        self.field1_farm1 = Field.objects.create(farm=self.farm1, name="North Field", size=10.0)
        self.crop1_field1 = Crop.objects.create(field=self.field1_farm1, crop_type="Wheat", planting_date=timezone.now().date(), is_harvested=False)
        self.log1_farm1 = ActivityLog.objects.create(farm=self.farm1, activity_type='preparation', timestamp=timezone.now())
        self.prep_log1 = PreparationLog.objects.create(activity_log=self.log1_farm1, field=self.field1_farm1, desc="Initial plow")

        # Data for other_farmer_user
        self.farm_other = Farm.objects.create(farmer=self.other_farmer_profile, name="Jane's Farm", location="Hillside", size=15.0)
        self.field_other = Field.objects.create(farm=self.farm_other, name="East Field", size=7.0)

        # URLs (assuming 'farm' is the app_name in urls.py)
        self.farm_list_url = reverse('farm:farm_list')
        self.farm_create_url = reverse('farm:farm_create')
        self.farm_detail_url = reverse('farm:farm_detail', args=[self.farm1.farm_id])
        self.farm_update_url = reverse('farm:farm_update', args=[self.farm1.farm_id])
        self.farm_delete_url = reverse('farm:farm_delete', args=[self.farm1.farm_id])
        self.farm_condition_update_url = reverse('farm:farm_condition_update', args=[self.farm1.farm_id])
        self.field_list_url = reverse('farm:field_list', args=[self.farm1.farm_id])
        self.field_create_url = reverse('farm:field_create', args=[self.farm1.farm_id])
        self.field_detail_url = reverse('farm:field_detail', args=[self.farm1.farm_id, self.field1_farm1.field_id])
        self.field_update_url = reverse('farm:field_update', args=[self.farm1.farm_id, self.field1_farm1.field_id])
        self.field_delete_url = reverse('farm:field_delete', args=[self.farm1.farm_id, self.field1_farm1.field_id])
        self.crop_detail_url = reverse('farm:crop_detail', args=[self.farm1.farm_id, self.crop1_field1.crop_id])
        self.activity_list_url = reverse('farm:activity_log_list', args=[self.farm1.farm_id])
        self.activity_create_url = reverse('farm:activity_log_create', args=[self.farm1.farm_id])
        self.activity_detail_url = reverse('farm:activity_log_detail', args=[self.farm1.farm_id, self.log1_farm1.log_id])
        self.activity_update_url = reverse('farm:activity_log_update', args=[self.farm1.farm_id, self.log1_farm1.log_id])
        self.activity_delete_url = reverse('farm:activity_log_delete', args=[self.farm1.farm_id, self.log1_farm1.log_id])
        self.ajax_specialized_form_url = reverse('farm:get_specialized_form', args=[self.farm1.farm_id])
        self.ajax_active_crops_url = reverse('farm:get_active_crops', args=[self.farm1.farm_id])

        # Login the main farmer user for most tests
        self.client.login(username=self.farmer_user.username, password=self.password)

    # --- Helper Methods ---
    def _assert_redirects_to_login(self, url, method='get', data=None):
        """Helper to test redirection for unauthenticated users."""
        self.client.logout() # Ensure user is logged out
        if method == 'get':
            response = self.client.get(url)
        else:
            response = self.client.post(url, data=data or {})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(settings.LOGIN_URL))
        self.client.login(username=self.farmer_user.username, password=self.password) # Log back in

    def _assert_farmer_required(self, url, method='get', data=None):
        """Helper to test views requiring a farmer profile."""
        # Use the non-farmer user
        self.client.login(username=self.other_user.username, password=self.password)
        if method == 'get':
            response = self.client.get(url)
        else:
            response = self.client.post(url, data=data or {})
        # Depending on implementation, it might redirect or show an error.
        # Here, farm_list creates a profile, farm_create tries to. Others might 404 or redirect.
        # We'll just check it doesn't give a 200 OK for the intended page.
        self.assertNotEqual(response.status_code, 200)
        self.client.login(username=self.farmer_user.username, password=self.password) # Log back in

    def _assert_ownership_required(self, url, method='get', data=None):
        """Helper to test that user must own the object (farm, field, etc.)."""
        # User farmerjoe is logged in, try accessing farmerjane's stuff
        if method == 'get':
            response = self.client.get(url)
        else:
            response = self.client.post(url, data=data or {})
        # Should result in 404 because get_object_or_404 fails ownership check
        self.assertEqual(response.status_code, 404)

    # --- Test Farm Views ---
    def test_farm_list_view(self):
        self._assert_redirects_to_login(self.farm_list_url)
        # self._assert_farmer_required(self.farm_list_url) # This view creates farmer profile

        response = self.client.get(self.farm_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'farm_list.html')
        self.assertIn('farms', response.context)
        self.assertContains(response, self.farm1.name)
        self.assertNotContains(response, self.farm_other.name) # Shouldn't see other farmer's farm

    def test_farm_create_view_get(self):
        self._assert_redirects_to_login(self.farm_create_url)
        response = self.client.get(self.farm_create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'farm_form.html')
        self.assertIsInstance(response.context['form'], FarmForm)

    def test_farm_create_view_post_success(self):
        self._assert_redirects_to_login(self.farm_create_url, method='post')
        farm_count_before = Farm.objects.count()
        condition_count_before = FarmCondition.objects.count()
        data = {'name': 'Newest Farm', 'location': 'Down the road', 'size': 5.0}
        response = self.client.post(self.farm_create_url, data)

        self.assertEqual(Farm.objects.count(), farm_count_before + 1)
        self.assertEqual(FarmCondition.objects.count(), condition_count_before + 1)
        new_farm = Farm.objects.get(name='Newest Farm')
        self.assertEqual(new_farm.farmer, self.farmer_profile)
        self.assertTrue(FarmCondition.objects.filter(farm=new_farm).exists())
        self.assertRedirects(response, reverse('farm:farm_detail', args=[new_farm.farm_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue('created successfully' in str(messages[0]))

    def test_farm_create_view_post_invalid(self):
        farm_count_before = Farm.objects.count()
        data = {'name': '', 'location': 'Invalid location', 'size': 5.0} # Empty name
        response = self.client.post(self.farm_create_url, data)
        self.assertEqual(Farm.objects.count(), farm_count_before) # No farm created
        self.assertEqual(response.status_code, 200) # Re-renders form
        self.assertTemplateUsed(response, 'farm_form.html')
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('name', response.context['form'].errors)

    def test_farm_detail_view(self):
        self._assert_redirects_to_login(self.farm_detail_url)
        # Test ownership
        other_farm_url = reverse('farm:farm_detail', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        response = self.client.get(self.farm_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'farm_detail.html')
        self.assertEqual(response.context['farm'], self.farm1)
        self.assertContains(response, self.farm1.name)
        self.assertContains(response, self.field1_farm1.name) # Check related data shown
        self.assertIn('analytics', response.context) # Check analytics dict exists

    def test_farm_update_view_get(self):
        self._assert_redirects_to_login(self.farm_update_url)
        other_farm_url = reverse('farm:farm_update', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        response = self.client.get(self.farm_update_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'farm_form.html')
        self.assertEqual(response.context['farm'], self.farm1)
        self.assertEqual(response.context['form'].instance, self.farm1)

    def test_farm_update_view_post_success(self):
        self._assert_redirects_to_login(self.farm_update_url, method='post')
        other_farm_url = reverse('farm:farm_update', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url, method='post')

        data = {'name': 'Joes Updated Farm', 'location': self.farm1.location, 'size': self.farm1.size}
        response = self.client.post(self.farm_update_url, data)
        self.farm1.refresh_from_db()
        self.assertEqual(self.farm1.name, 'Joes Updated Farm')
        self.assertRedirects(response, self.farm_detail_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('updated successfully' in str(messages[0]))

    def test_farm_delete_view_get(self):
        self._assert_redirects_to_login(self.farm_delete_url)
        other_farm_url = reverse('farm:farm_delete', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        response = self.client.get(self.farm_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'farm_confirm_delete.html')
        self.assertEqual(response.context['farm'], self.farm1)

    def test_farm_delete_view_post_success(self):
        self._assert_redirects_to_login(self.farm_delete_url, method='post')
        other_farm_url = reverse('farm:farm_delete', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url, method='post')

        farm_id_to_delete = self.farm1.farm_id
        farm_count_before = Farm.objects.count()
        response = self.client.post(self.farm_delete_url)
        self.assertEqual(Farm.objects.count(), farm_count_before - 1)
        with self.assertRaises(Farm.DoesNotExist):
            Farm.objects.get(farm_id=farm_id_to_delete)
        self.assertRedirects(response, self.farm_list_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('deleted successfully' in str(messages[0]))

    def test_farm_condition_update_view(self):
        self._assert_redirects_to_login(self.farm_condition_update_url)
        other_farm_url = reverse('farm:farm_condition_update', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)
        self._assert_ownership_required(other_farm_url, method='post')

        # GET
        response_get = self.client.get(self.farm_condition_update_url)
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'farm_condition_form.html')
        self.assertEqual(response_get.context['form'].instance, self.farm1_condition)

        # POST
        data = {'soil_ph': 7.0, 'soil_moisture': 50.0, 'rainfall': 100, 'max_daily_temp': 28, 'day_length': 11}
        response_post = self.client.post(self.farm_condition_update_url, data)
        self.farm1_condition.refresh_from_db()
        self.assertEqual(self.farm1_condition.soil_ph, 7.0)
        self.assertEqual(self.farm1_condition.soil_moisture, 50.0)
        self.assertRedirects(response_post, self.farm_detail_url)
        messages = list(get_messages(response_post.wsgi_request))
        self.assertTrue('Farm conditions updated' in str(messages[0]))

    # --- Test Field Views (similar patterns: auth, ownership, get, post, delete) ---
    def test_field_list_view(self):
        self._assert_redirects_to_login(self.field_list_url)
        other_farm_url = reverse('farm:field_list', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        response = self.client.get(self.field_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'field_list.html')
        self.assertEqual(response.context['farm'], self.farm1)
        self.assertContains(response, self.field1_farm1.name)

    def test_field_create_view_post_success(self):
        self._assert_redirects_to_login(self.field_create_url, method='post')
        other_farm_url = reverse('farm:field_create', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url, method='post')

        field_count_before = Field.objects.filter(farm=self.farm1).count()
        data = {'name': 'South Field', 'size': 4.0, 'location_within_farm': 'Bottom corner'}
        response = self.client.post(self.field_create_url, data)
        self.assertEqual(Field.objects.filter(farm=self.farm1).count(), field_count_before + 1)
        new_field = Field.objects.get(farm=self.farm1, name='South Field')
        self.assertRedirects(response, reverse('farm:field_detail', args=[self.farm1.farm_id, new_field.field_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Field' in str(messages[0]) and 'created successfully' in str(messages[0]))

    # --- Test Crop Views ---
    def test_crop_detail_view(self):
        self._assert_redirects_to_login(self.crop_detail_url)
        # Test ownership (try accessing crop in other farmer's farm)
        other_crop = Crop.objects.create(field=self.field_other, crop_type='Barley', planting_date=timezone.now().date())
        other_crop_url = reverse('farm:crop_detail', args=[self.farm_other.farm_id, other_crop.crop_id])
        self._assert_ownership_required(other_crop_url) # Should fail because farm ID is wrong
        # Also test accessing a valid crop ID but with the wrong farm ID in URL
        wrong_farm_url = reverse('farm:crop_detail', args=[self.farm_other.farm_id, self.crop1_field1.crop_id])
        self._assert_ownership_required(wrong_farm_url) # Should fail because farm ID is wrong

        response = self.client.get(self.crop_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'crop_detail.html')
        self.assertEqual(response.context['crop'], self.crop1_field1)
        self.assertEqual(response.context['farm'], self.farm1)

    # --- Test ActivityLog Views ---
    def test_activity_log_list_view(self):
        self._assert_redirects_to_login(self.activity_list_url)
        other_farm_url = reverse('farm:activity_log_list', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        response = self.client.get(self.activity_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activity_log_list.html')
        self.assertContains(response, self.log1_farm1.get_activity_type_display()) # Check log shown

        # Test filtering
        response_filtered = self.client.get(self.activity_list_url + '?type=preparation')
        self.assertContains(response_filtered, self.log1_farm1.get_activity_type_display())
        response_filtered_wrong = self.client.get(self.activity_list_url + '?type=planting')
        self.assertNotContains(response_filtered_wrong, self.log1_farm1.get_activity_type_display())


    def test_activity_log_create_view_get(self):
        self._assert_redirects_to_login(self.activity_create_url)
        response = self.client.get(self.activity_create_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'activity_log_form.html')
        self.assertIsInstance(response.context['activity_form'], ActivityLogForm)
        self.assertIsNone(response.context['specialized_form']) # Initially None

    def test_activity_log_create_preparation_post_success(self):
        self._assert_redirects_to_login(self.activity_create_url, method='post')
        log_count_before = ActivityLog.objects.count()
        prep_count_before = PreparationLog.objects.count()
        timestamp_now = timezone.now()

        data = {
            'activity_type': 'preparation',
            'timestamp': timestamp_now.strftime('%Y-%m-%dT%H:%M'),
            # PreparationLogForm fields
            'field': self.field1_farm1.pk,
            'equipment_used': 'Spade',
            'desc': 'Digging edges'
        }
        response = self.client.post(self.activity_create_url, data)

        self.assertEqual(ActivityLog.objects.count(), log_count_before + 1)
        self.assertEqual(PreparationLog.objects.count(), prep_count_before + 1)
        new_log = ActivityLog.objects.latest('timestamp')
        self.assertEqual(new_log.activity_type, 'preparation')
        self.assertEqual(new_log.farm, self.farm1)
        self.assertTrue(hasattr(new_log, 'preparationlog'))
        self.assertEqual(new_log.preparationlog.field, self.field1_farm1)
        self.assertEqual(new_log.preparationlog.equipment_used, 'Spade')
        self.assertRedirects(response, reverse('farm:activity_log_detail', args=[self.farm1.farm_id, new_log.log_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('preparation activity logged' in str(messages[0]))

    def test_activity_log_create_planting_post_success(self):
        self._assert_redirects_to_login(self.activity_create_url, method='post')
        log_count_before = ActivityLog.objects.count()
        plant_count_before = PlantingLog.objects.count()
        crop_count_before = Crop.objects.count()
        timestamp_now = timezone.now()
        harvest_date = timestamp_now.date() + timezone.timedelta(days=90)

        data = {
            'activity_type': 'planting',
            'timestamp': timestamp_now.strftime('%Y-%m-%dT%H:%M'),
            # PlantingLogForm fields
            'field': self.field1_farm1.pk,
            'seed_quantity': 5.0,
            'seed_variety': 'Early Corn',
            'fertilizer_applied': 2.0,
            'crop_type': 'Corn', # From PlantingLogForm extra field
            'expected_harvest_date': harvest_date.strftime('%Y-%m-%d') # From PlantingLogForm extra field
        }
        response = self.client.post(self.activity_create_url, data)

        self.assertEqual(ActivityLog.objects.count(), log_count_before + 1)
        self.assertEqual(PlantingLog.objects.count(), plant_count_before + 1)
        self.assertEqual(Crop.objects.count(), crop_count_before + 1) # Crop created

        new_log = ActivityLog.objects.latest('timestamp')
        self.assertEqual(new_log.activity_type, 'planting')
        self.assertTrue(hasattr(new_log, 'plantinglog'))
        self.assertEqual(new_log.plantinglog.field, self.field1_farm1)
        self.assertEqual(new_log.plantinglog.seed_variety, 'Early Corn')

        new_crop = Crop.objects.latest('planting_date')
        self.assertEqual(new_crop.field, self.field1_farm1)
        self.assertEqual(new_crop.crop_type, 'Corn')
        self.assertEqual(new_crop.planting_activity, new_log.plantinglog)
        self.assertEqual(new_crop.expected_harvest_date, harvest_date)
        self.assertFalse(new_crop.is_harvested)

        self.assertRedirects(response, reverse('farm:activity_log_detail', args=[self.farm1.farm_id, new_log.log_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Planting activity logged' in str(messages[0]) and 'new Corn crop has been added' in str(messages[0]))

    def test_activity_log_create_harvesting_post_success(self):
        self._assert_redirects_to_login(self.activity_create_url, method='post')
        log_count_before = ActivityLog.objects.count()
        harvest_count_before = HarvestingLog.objects.count()
        timestamp_now = timezone.now()

        # Ensure the crop is not harvested before the test
        self.crop1_field1.is_harvested = False
        self.crop1_field1.save()

        data = {
            'activity_type': 'harvesting',
            'timestamp': timestamp_now.strftime('%Y-%m-%dT%H:%M'),
            # HarvestingLogForm fields
            'crop': self.crop1_field1.pk,
            'yield_amount': 2000.0,
            'harvest_quality': 'excellent'
        }
        response = self.client.post(self.activity_create_url, data)

        self.assertEqual(ActivityLog.objects.count(), log_count_before + 1)
        self.assertEqual(HarvestingLog.objects.count(), harvest_count_before + 1)

        new_log = ActivityLog.objects.latest('timestamp')
        self.assertEqual(new_log.activity_type, 'harvesting')
        self.assertTrue(hasattr(new_log, 'harvestinglog'))
        self.assertEqual(new_log.harvestinglog.crop, self.crop1_field1)
        self.assertEqual(new_log.harvestinglog.yield_amount, 2000.0)

        # Check the crop is marked as harvested
        self.crop1_field1.refresh_from_db()
        self.assertTrue(self.crop1_field1.is_harvested)
        self.assertEqual(self.crop1_field1.harvest_date, timestamp_now.date())

        self.assertRedirects(response, reverse('farm:activity_log_detail', args=[self.farm1.farm_id, new_log.log_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Harvesting activity' in str(messages[0]) and 'marked as harvested' in str(messages[0]))

    def test_activity_log_update_view(self):
        self._assert_redirects_to_login(self.activity_update_url, method='post')
        other_log_url = reverse('farm:activity_log_update', args=[self.farm_other.farm_id, self.log1_farm1.log_id]) # Wrong farm ID
        self._assert_ownership_required(other_log_url, method='post')

        # GET
        response_get = self.client.get(self.activity_update_url)
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'activity_log_form.html')
        self.assertEqual(response_get.context['activity'].pk, self.log1_farm1.pk)
        self.assertIsInstance(response_get.context['activity_form'], ActivityLogForm)
        self.assertIsInstance(response_get.context['specialized_form'], PreparationLogForm) # Correct specialized form loaded
        # Check activity_type is disabled
        self.assertTrue(response_get.context['activity_form'].fields['activity_type'].widget.attrs.get('disabled'))


        # POST Update Description
        new_desc = "Updated plowing description"
        data = {
            'activity_type': 'preparation', # Must be included even if disabled
            'timestamp': self.log1_farm1.timestamp.strftime('%Y-%m-%dT%H:%M'),
            # PreparationLogForm fields
            'field': self.field1_farm1.pk,
            'equipment_used': self.prep_log1.equipment_used,
            'desc': new_desc
        }
        response_post = self.client.post(self.activity_update_url, data)
        self.prep_log1.refresh_from_db()
        self.assertEqual(self.prep_log1.desc, new_desc)
        self.assertRedirects(response_post, self.activity_detail_url)
        messages = list(get_messages(response_post.wsgi_request))
        self.assertTrue('Activity log updated successfully' in str(messages[0]))

    def test_activity_log_delete_preparation_success(self):
        self._assert_redirects_to_login(self.activity_delete_url, method='post')
        other_log_url = reverse('farm:activity_log_delete', args=[self.farm_other.farm_id, self.log1_farm1.log_id]) # Wrong farm ID
        self._assert_ownership_required(other_log_url, method='post')

        log_id_to_delete = self.log1_farm1.log_id
        log_count_before = ActivityLog.objects.count()
        prep_count_before = PreparationLog.objects.count()

        # GET Confirmation Page
        response_get = self.client.get(self.activity_delete_url)
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'activity_log_confirm_delete.html')

        # POST Delete
        response_post = self.client.post(self.activity_delete_url)
        self.assertEqual(ActivityLog.objects.count(), log_count_before - 1)
        self.assertEqual(PreparationLog.objects.count(), prep_count_before - 1) # Specialized log also deleted (cascade)
        with self.assertRaises(ActivityLog.DoesNotExist):
            ActivityLog.objects.get(log_id=log_id_to_delete)
        self.assertRedirects(response_post, self.activity_list_url)
        messages = list(get_messages(response_post.wsgi_request))
        self.assertTrue('preparation activity deleted' in str(messages[0]).lower())

    def test_activity_log_delete_planting_with_dependencies_fails(self):
        """Test cannot delete planting log if crop has maintenance/harvesting."""
        # Create planting log and its crop
        plant_log = ActivityLog.objects.create(farm=self.farm1, activity_type='planting', timestamp=timezone.now())
        plant_spec = PlantingLog.objects.create(activity_log=plant_log, field=self.field1_farm1, seed_variety='Test Seeds')
        crop = Crop.objects.create(field=self.field1_farm1, planting_activity=plant_spec, crop_type='Test Crop', is_harvested=False)
        # Create a dependent maintenance log
        maint_log = ActivityLog.objects.create(farm=self.farm1, activity_type='maintenance', timestamp=timezone.now())
        MaintenanceLog.objects.create(activity_log=maint_log, crop=crop)

        delete_url = reverse('farm:activity_log_delete', args=[self.farm1.farm_id, plant_log.log_id])
        response = self.client.post(delete_url)

        self.assertTrue(ActivityLog.objects.filter(pk=plant_log.pk).exists()) # Log not deleted
        self.assertTrue(Crop.objects.filter(pk=crop.pk).exists()) # Crop not deleted
        self.assertRedirects(response, reverse('farm:activity_log_detail', args=[self.farm1.farm_id, plant_log.log_id]))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('Cannot delete this planting activity' in str(messages[0]))

    def test_activity_log_delete_planting_no_dependencies_success(self):
        """Test deleting planting log also deletes the associated crop."""
        # Create planting log and its crop
        plant_log = ActivityLog.objects.create(farm=self.farm1, activity_type='planting', timestamp=timezone.now())
        plant_spec = PlantingLog.objects.create(activity_log=plant_log, field=self.field1_farm1, seed_variety='Test Seeds')
        crop = Crop.objects.create(field=self.field1_farm1, planting_activity=plant_spec, crop_type='Test Crop', is_harvested=False)

        log_id_to_delete = plant_log.log_id
        crop_id_to_delete = crop.crop_id
        log_count_before = ActivityLog.objects.count()
        crop_count_before = Crop.objects.count()

        delete_url = reverse('farm:activity_log_delete', args=[self.farm1.farm_id, plant_log.log_id])
        response = self.client.post(delete_url)

        self.assertEqual(ActivityLog.objects.count(), log_count_before - 1)
        self.assertEqual(Crop.objects.count(), crop_count_before - 1) # Crop deleted
        with self.assertRaises(ActivityLog.DoesNotExist):
            ActivityLog.objects.get(log_id=log_id_to_delete)
        with self.assertRaises(Crop.DoesNotExist):
            Crop.objects.get(crop_id=crop_id_to_delete)
        self.assertRedirects(response, self.activity_list_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('planting activity deleted' in str(messages[0]).lower())

    def test_activity_log_delete_harvesting_unmarks_crop(self):
        """Test deleting harvesting log unmarks the crop as harvested."""
        # Create harvesting log and mark crop as harvested
        harvest_log = ActivityLog.objects.create(farm=self.farm1, activity_type='harvesting', timestamp=timezone.now())
        harvest_spec = HarvestingLog.objects.create(activity_log=harvest_log, crop=self.crop1_field1, yield_amount=100)
        self.crop1_field1.is_harvested = True
        self.crop1_field1.harvest_date = timezone.now().date()
        self.crop1_field1.save()

        log_id_to_delete = harvest_log.log_id
        log_count_before = ActivityLog.objects.count()

        delete_url = reverse('farm:activity_log_delete', args=[self.farm1.farm_id, harvest_log.log_id])
        response = self.client.post(delete_url)

        self.assertEqual(ActivityLog.objects.count(), log_count_before - 1)
        with self.assertRaises(ActivityLog.DoesNotExist):
            ActivityLog.objects.get(log_id=log_id_to_delete)

        # Check crop is unmarked
        self.crop1_field1.refresh_from_db()
        self.assertFalse(self.crop1_field1.is_harvested)
        self.assertIsNone(self.crop1_field1.harvest_date)

        self.assertRedirects(response, self.activity_list_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue('harvesting activity deleted' in str(messages[0]).lower())

    # --- Test AJAX Views ---
    def test_get_specialized_form_ajax(self):
        self._assert_redirects_to_login(self.ajax_specialized_form_url)
        other_farm_url = reverse('farm:get_specialized_form', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        # Test for preparation
        response_prep = self.client.get(self.ajax_specialized_form_url, {'activity_type': 'preparation'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_prep.status_code, 200)
        self.assertEqual(response_prep['content-type'], 'application/json')
        json_prep = response_prep.json()
        self.assertIn('html', json_prep)
        self.assertIn('id_field', json_prep['html']) # Check if field element is in HTML
        self.assertIn('id_equipment_used', json_prep['html'])

        # Test for planting
        response_plant = self.client.get(self.ajax_specialized_form_url, {'activity_type': 'planting'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_plant.status_code, 200)
        json_plant = response_plant.json()
        self.assertIn('html', json_plant)
        self.assertIn('id_seed_quantity', json_plant['html'])
        self.assertIn('id_crop_type', json_plant['html']) # Check for the extra field

        # Test for invalid type
        response_invalid = self.client.get(self.ajax_specialized_form_url, {'activity_type': 'invalid'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_invalid.status_code, 200)
        json_invalid = response_invalid.json()
        self.assertEqual(json_invalid['html'], '')

    def test_get_active_crops_ajax(self):
        self._assert_redirects_to_login(self.ajax_active_crops_url)
        other_farm_url = reverse('farm:get_active_crops', args=[self.farm_other.farm_id])
        self._assert_ownership_required(other_farm_url)

        # Create another active crop in another field
        field2_farm1 = Field.objects.create(farm=self.farm1, name="South Field", size=8.0)
        crop2_field2 = Crop.objects.create(field=field2_farm1, crop_type="Barley", planting_date=timezone.now().date(), is_harvested=False)

        # Get all active crops for farm1
        response_all = self.client.get(self.ajax_active_crops_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_all.status_code, 200)
        self.assertEqual(response_all['content-type'], 'application/json')
        json_all = response_all.json()
        self.assertIn('crops', json_all)
        self.assertEqual(len(json_all['crops']), 2) # crop1_field1 and crop2_field2
        crop_names = [c['name'] for c in json_all['crops']]
        self.assertIn(f"{self.crop1_field1.crop_type} - {self.field1_farm1.name}", crop_names)
        self.assertIn(f"{crop2_field2.crop_type} - {field2_farm1.name}", crop_names)

        # Get active crops only for field1_farm1
        response_field1 = self.client.get(self.ajax_active_crops_url, {'field_id': self.field1_farm1.pk}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_field1.status_code, 200)
        json_field1 = response_field1.json()
        self.assertEqual(len(json_field1['crops']), 1)
        self.assertEqual(json_field1['crops'][0]['id'], str(self.crop1_field1.crop_id))