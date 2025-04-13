from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages 
from unittest.mock import patch, MagicMock
from .forms import CustomUserCreationForm

User = get_user_model()

# --- Test untuk Forms ---
class CustomUserCreationFormTests(TestCase):

    def test_form_valid_data(self):
        """Test form is valid with correct data."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'ValidPassword123!',
            'password2': 'ValidPassword123!',
            'phone_no': '1234567890'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_form_password_mismatch(self):
        """Test form detects password mismatch."""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'ValidPassword123!',
            'password2': 'DifferentPassword!', # Password beda
            'phone_no': '1234567890'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        self.assertIn('The two password fields didn’t match.', form.errors['password2'])

    def test_form_existing_username(self):
        """Test form detects existing username."""
        User.objects.create_user(username='existinguser', password='password')
        form_data = {
            'username': 'existinguser', 
            'email': 'test@example.com',
            'password': 'ValidPassword123!',
            'password2': 'ValidPassword123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('A user with that username already exists.', form.errors['username'])

    def test_form_existing_email(self):
        """Test form detects existing email."""
        User.objects.create_user(username='anotheruser', email='existing@example.com', password='password')
        form_data = {
            'username': 'testuser',
            'email': 'existing@example.com', 
            'password': 'ValidPassword123!',
            'password2': 'ValidPassword123!',
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('A user with that email already exists.', form.errors['email'])

    def test_form_missing_required_fields(self):
        """Test form requires username, email, passwords."""
        form_data = {} 
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password', form.errors) 
        self.assertIn('password2', form.errors)


# --- Test untuk Views ---
class AuthenticationViewsTests(TestCase):

    def setUp(self):
        """Setup data yang dibutuhkan untuk semua test di class ini."""
        self.client = Client()
        self.user_password = 'StrongPassword123!'
        # User biasa tanpa 2FA
        self.user_no_2fa = User.objects.create_user(
            username='user_no_2fa',
            email='no2fa@example.com',
            password=self.user_password
        )
        # User dengan 2FA aktif (dan punya secret)
        self.user_with_2fa = User.objects.create_user(
            username='user_with_2fa',
            email='with2fa@example.com',
            password=self.user_password,
            is_2fa_enabled=True,
            otp_secret='BASE32SECRETFORTESTING123'
        )
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.logout_url = reverse('logout')
        self.setup_2fa_url = reverse('setup_2fa')
        self.verify_2fa_url = reverse('verify_2fa')
        self.dashboard_url = reverse('dashboard') 

    # == Test user_login View ==
    def test_login_view_get(self):
        """Test GET request ke login page."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')

    @patch('authentication.views.authenticate') 
    def test_login_success_no_2fa(self, mock_authenticate):
        """Test login berhasil untuk user tanpa 2FA."""
        mock_authenticate.return_value = self.user_no_2fa 
        response = self.client.post(self.login_url, {
            'username': self.user_no_2fa.username,
            'password': self.user_password
        })
        mock_authenticate.assert_called_once_with(request=response.wsgi_request, username=self.user_no_2fa.username, password=self.user_password)
        self.assertRedirects(response, self.dashboard_url)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user_no_2fa.id)

    @patch('authentication.views.authenticate')
    def test_login_success_with_2fa_redirects_to_verify(self, mock_authenticate):
        """Test login berhasil user dgn 2FA redirect ke verify_2fa."""
        mock_authenticate.return_value = self.user_with_2fa
        response = self.client.post(self.login_url, {
            'username': self.user_with_2fa.username,
            'password': self.user_password
        })
        mock_authenticate.assert_called_once_with(request=response.wsgi_request, username=self.user_with_2fa.username, password=self.user_password)
        self.assertRedirects(response, self.verify_2fa_url)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertIn('2fa_user_id', self.client.session)
        self.assertEqual(self.client.session['2fa_user_id'], self.user_with_2fa.id)

    @patch('authentication.views.authenticate')
    def test_login_invalid_credentials(self, mock_authenticate):
        """Test login gagal karena username/password salah."""
        mock_authenticate.return_value = None 
        response = self.client.post(self.login_url, {
            'username': 'wronguser',
            'password': 'wrongpassword'
        })
        mock_authenticate.assert_called_once_with(request=response.wsgi_request, username='wronguser', password='wrongpassword')
        self.assertRedirects(response, self.login_url) 
        self.assertNotIn('_auth_user_id', self.client.session) 
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid username or password")

    # == Test register View ==
    def test_register_view_get(self):
        """Test GET request ke register page."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')
        self.assertIn('form', response.context)
        self.assertIsInstance(response.context['form'], CustomUserCreationForm)

    @patch.object(User, 'generate_otp_secret', return_value=None) 
    def test_register_success(self, mock_generate_secret):
        """Test registrasi berhasil."""
        user_count_before = User.objects.count()
        form_data = {
            'username': 'new_registered_user',
            'email': 'new@example.com',
            'password': self.user_password,
            'password2': self.user_password,
            'phone_no': '987654321'
        }
        response = self.client.post(self.register_url, form_data)

        self.assertEqual(User.objects.count(), user_count_before + 1)
        new_user = User.objects.get(username='new_registered_user')
        self.assertEqual(new_user.email, 'new@example.com')
        self.assertEqual(new_user.phone_no, '987654321')

        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(int(self.client.session['_auth_user_id']), new_user.id)

        mock_generate_secret.assert_called_once()
        self.assertRedirects(response, self.setup_2fa_url)

    def test_register_invalid_data(self):
        """Test registrasi gagal karena data form tidak valid."""
        user_count_before = User.objects.count()
        form_data = { 
            'username': 'fail_register_user',
            'email': 'fail@example.com',
            'password': 'password1',
            'password2': 'password2',
        }
        response = self.client.post(self.register_url, form_data)
        self.assertEqual(User.objects.count(), user_count_before)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')
        self.assertIn('form', response.context)
        self.assertFalse(response.context['form'].is_valid()) 
        self.assertIn('password2', response.context['form'].errors)

    # == Test logout_view View ==
    def test_logout_view(self):
        """Test logout berhasil."""
        self.client.login(username=self.user_no_2fa.username, password=self.user_password)
        self.assertIn('_auth_user_id', self.client.session)
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, self.login_url)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_view_requires_login(self):
        """Test logout view tidak bisa diakses user anonim."""
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.logout_url}')

    # == Test setup_2fa View ==
    def test_setup_2fa_view_get_requires_login(self):
        """Test GET setup_2fa view tidak bisa diakses user anonim."""
        response = self.client.get(self.setup_2fa_url)
        self.assertRedirects(response, f'{self.login_url}?next={self.setup_2fa_url}')

    @patch('authentication.views.qrcode')
    @patch('authentication.views.pyotp')
    def test_setup_2fa_view_get_authenticated(self, mock_pyotp, mock_qrcode):
        """Test GET setup_2fa view oleh user terautentikasi."""
        mock_totp_instance = MagicMock()
        mock_totp_instance.provisioning_uri.return_value = "otpauth://totp/AgriTrace:test@example.com?secret=TESTSECRET&issuer=AgriTrace"
        mock_pyotp.TOTP.return_value = mock_totp_instance
        mock_qrcode_instance = MagicMock()
        mock_qrcode.QRCode.return_value = mock_qrcode_instance

        self.client.login(username=self.user_no_2fa.username, password=self.user_password)
        response = self.client.get(self.setup_2fa_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/setup_2fa.html')
        self.assertIn('qr_code_b64', response.context)
        self.assertIn('otp_secret', response.context)
        mock_totp_instance.provisioning_uri.assert_called_once_with(
            name=self.user_no_2fa.email, issuer_name="AgriTrace"
        )

    @patch('authentication.views.pyotp')
    def test_setup_2fa_post_valid_code(self, mock_pyotp):
        """Test POST ke setup_2fa dengan kode valid."""
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = True 
        mock_pyotp.TOTP.return_value = mock_totp_instance

        # Login user (yg belum aktif 2FA nya)
        self.client.login(username=self.user_no_2fa.username, password=self.user_password)
        self.assertFalse(User.objects.get(id=self.user_no_2fa.id).is_2fa_enabled)

        response = self.client.post(self.setup_2fa_url, {'verification_code': '123456'})

        updated_user = User.objects.get(id=self.user_no_2fa.id)
        self.assertTrue(updated_user.is_2fa_enabled)

        self.assertRedirects(response, self.dashboard_url)
        mock_pyotp.TOTP.assert_called_once_with(updated_user.otp_secret)
        mock_totp_instance.verify.assert_called_once_with('123456')
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Two-factor authentication successfully enabled!")

    @patch('authentication.views.pyotp')
    def test_setup_2fa_post_invalid_code(self, mock_pyotp):
        """Test POST ke setup_2fa dengan kode invalid."""
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = False
        mock_pyotp.TOTP.return_value = mock_totp_instance

        self.client.login(username=self.user_no_2fa.username, password=self.user_password)
        user_before = User.objects.get(id=self.user_no_2fa.id)
        self.assertFalse(user_before.is_2fa_enabled)

        response = self.client.post(self.setup_2fa_url, {'verification_code': 'wrongcode'})

        user_after = User.objects.get(id=self.user_no_2fa.id)
        self.assertFalse(user_after.is_2fa_enabled)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/setup_2fa.html')
        mock_pyotp.TOTP.assert_called_once_with(user_after.otp_secret)
        mock_totp_instance.verify.assert_called_once_with('wrongcode')
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid verification code. Please try again.")

    # == Test verify_2fa View ==
    def test_verify_2fa_get_no_session(self):
        """Test GET verify_2fa tanpa session key."""
        response = self.client.get(self.verify_2fa_url)
        self.assertRedirects(response, self.login_url)

    def test_verify_2fa_get_with_session(self):
        """Test GET verify_2fa dengan session key valid."""
        session = self.client.session
        session['2fa_user_id'] = self.user_with_2fa.id
        session.save()

        response = self.client.get(self.verify_2fa_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/verify_2fa.html')

    def test_verify_2fa_get_invalid_user_id_in_session(self):
        """Test GET verify_2fa dgn user ID di session tapi user tdk ada."""
        non_existent_user_id = 9999
        session = self.client.session
        session['2fa_user_id'] = non_existent_user_id
        session.save()

        response = self.client.get(self.verify_2fa_url)
        self.assertRedirects(response, self.login_url)

    @patch('authentication.views.login')
    @patch('authentication.views.pyotp')
    def test_verify_2fa_post_valid_code(self, mock_pyotp, mock_login):
        """Test POST ke verify_2fa dengan kode valid."""
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = True
        mock_pyotp.TOTP.return_value = mock_totp_instance

        session = self.client.session
        session['2fa_user_id'] = self.user_with_2fa.id
        session.save()

        response = self.client.post(self.verify_2fa_url, {'verification_code': '123456'})

        mock_pyotp.TOTP.assert_called_once_with(self.user_with_2fa.otp_secret)
        mock_totp_instance.verify.assert_called_once_with('123456')
        self.assertNotIn('2fa_user_id', self.client.session)
        mock_login.assert_called_once()
        args, kwargs = mock_login.call_args
        self.assertEqual(args[0], response.wsgi_request)
        self.assertEqual(args[1], self.user_with_2fa)
        self.assertRedirects(response, self.dashboard_url)


    @patch('authentication.views.login')
    @patch('authentication.views.pyotp')
    def test_verify_2fa_post_invalid_code(self, mock_pyotp, mock_login):
        """Test POST ke verify_2fa dengan kode invalid."""
        mock_totp_instance = MagicMock()
        mock_totp_instance.verify.return_value = False
        mock_pyotp.TOTP.return_value = mock_totp_instance
        session = self.client.session
        session['2fa_user_id'] = self.user_with_2fa.id
        session.save()

        response = self.client.post(self.verify_2fa_url, {'verification_code': 'wrongcode'})

        mock_pyotp.TOTP.assert_called_once_with(self.user_with_2fa.otp_secret)
        mock_totp_instance.verify.assert_called_once_with('wrongcode')
        self.assertIn('2fa_user_id', self.client.session)
        mock_login.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/verify_2fa.html')
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Invalid verification code. Please try again.")