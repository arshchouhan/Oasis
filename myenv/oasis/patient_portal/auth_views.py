import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify

from .models import User


def _dashboard_for(user):
    return 'doctor_dashboard' if user.account_type == User.AccountType.DOCTOR else 'patient_dashboard'


def account_choice(request):
    if request.user.is_authenticated:
        return redirect(_dashboard_for(request.user))
    return render(request, 'patient_portal/auth/account_choice.html')


def patient_home(request):
    """Patient portal entry point: guests enter the patient sign-in flow."""
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect(_dashboard_for(request.user))


def _available_username(value):
    """Create a unique username when a registrant does not choose one."""
    stem = slugify(value.split('@')[0])[:140] or 'user'
    candidate = stem
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        suffix += 1
        candidate = f'{stem[:150 - len(str(suffix)) - 1]}-{suffix}'
    return candidate


def register(request, forced_role=None):
    requested_role = forced_role or request.POST.get('account_type', request.GET.get('role', ''))
    # An authenticated patient may deliberately create a separate doctor
    # account. Keep the explicit role-registration flow accessible instead of
    # silently returning them to their existing patient dashboard.
    if request.user.is_authenticated and requested_role not in User.AccountType.values:
        return redirect(_dashboard_for(request.user))

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        password_confirmation = request.POST.get('password_confirmation', '')
        account_type = forced_role or request.POST.get('account_type', User.AccountType.PATIENT)

        if account_type not in User.AccountType.values:
            messages.error(request, 'Choose whether you are creating a patient or doctor account.')
        elif not all((first_name, last_name, email, password)):
            messages.error(request, 'Please complete your name, email, and password.')
        elif password != password_confirmation:
            messages.error(request, 'The passwords do not match.')
        else:
            try:
                validate_email(email)
                validate_password(password)
                if User.objects.filter(email__iexact=email).exists():
                    raise ValidationError('An account already exists with this email address.')

                username = username or _available_username(email)
                if User.objects.filter(username__iexact=username).exists():
                    raise ValidationError('That username is already in use.')

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    account_type=account_type,
                )
                login(request, user, backend='patient_portal.backends.EmailOrUsernameBackend')
                return redirect(_dashboard_for(user))
            except (ValidationError, IntegrityError) as error:
                message = error.messages[0] if hasattr(error, 'messages') else str(error)
                messages.error(request, message)

    return render(request, 'patient_portal/auth/register.html', {
        'selected_account_type': requested_role if requested_role in User.AccountType.values else User.AccountType.PATIENT,
        'portal_role': forced_role,
    })


def login_view(request, forced_role=None):
    requested_role = forced_role or request.GET.get('role', '')
    if request.user.is_authenticated:
        # The account-choice page may deliberately send a signed-in doctor to
        # Patient login (or the reverse). End that session so the selected
        # login form can be used without a manual refresh.
        if requested_role in User.AccountType.values and requested_role != request.user.account_type:
            logout(request)
        else:
            return redirect(_dashboard_for(request.user))

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        account_type = forced_role or request.POST.get('account_type', User.AccountType.PATIENT)
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            messages.error(request, 'Incorrect username/email or password.')
        elif account_type not in User.AccountType.values or user.account_type != account_type:
            messages.error(request, 'This account belongs to a different dashboard. Choose the correct account type.')
        else:
            login(request, user)
            next_url = request.POST.get('next', '')
            if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
                return redirect(next_url)
            return redirect(_dashboard_for(user))

    return render(request, 'patient_portal/auth/login.html', {
        'next': request.GET.get('next', ''),
        'selected_account_type': forced_role or request.POST.get('account_type', requested_role or User.AccountType.PATIENT),
        'portal_role': forced_role,
    })


def patient_login(request):
    return login_view(request, User.AccountType.PATIENT)


def doctor_login(request):
    return login_view(request, User.AccountType.DOCTOR)


def patient_register(request):
    return register(request, User.AccountType.PATIENT)


def doctor_register(request):
    return register(request, User.AccountType.DOCTOR)


def logout_view(request):
    # Dashboard notices should not leak into the next account's login screen.
    list(get_messages(request))
    logout(request)
    # A neutral landing page prevents a logged-out portal session from being
    # sent into either the patient or doctor flow automatically.
    return redirect('site_home')


def google_login(request):
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, 'Google sign-in is not configured yet.')
        return redirect('login')

    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    callback_url = request.build_absolute_uri(reverse('google_callback'))
    query = urlencode({
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'prompt': 'select_account',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{query}')


def google_callback(request):
    expected_state = request.session.pop('google_oauth_state', '')
    if not expected_state or not secrets.compare_digest(expected_state, request.GET.get('state', '')):
        return HttpResponseBadRequest('Invalid Google sign-in state.')
    if request.GET.get('error') or not request.GET.get('code'):
        messages.error(request, 'Google sign-in was cancelled or failed.')
        return redirect('login')

    callback_url = request.build_absolute_uri(reverse('google_callback'))
    token_request = Request(
        'https://oauth2.googleapis.com/token',
        data=urlencode({
            'code': request.GET['code'],
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': callback_url,
            'grant_type': 'authorization_code',
        }).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urlopen(token_request, timeout=10) as response:
            token = json.load(response)
        profile_request = Request(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f"Bearer {token['access_token']}"},
        )
        with urlopen(profile_request, timeout=10) as response:
            profile = json.load(response)
    except Exception:
        messages.error(request, 'Google sign-in could not be completed. Please try again.')
        return redirect('login')

    email = profile.get('email', '').lower()
    google_sub = profile.get('sub', '')
    if not email or not google_sub or not profile.get('email_verified'):
        messages.error(request, 'Google did not provide a verified email address.')
        return redirect('login')

    user = User.objects.filter(google_sub=google_sub).first() or User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User(
            username=_available_username(email),
            email=email,
            first_name=profile.get('given_name', ''),
            last_name=profile.get('family_name', ''),
            google_sub=google_sub,
        )
        user.set_unusable_password()
    elif not user.google_sub:
        user.google_sub = google_sub
    user.save()
    login(request, user, backend='patient_portal.backends.EmailOrUsernameBackend')
    return redirect(_dashboard_for(user))
