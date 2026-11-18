import logging
import os

from django import forms
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from patient_portal.models import ColourVisionSession, MarketplaceProduct, User


def _dashboard_for(user):
    return 'doctor_dashboard' if user.account_type == 'doctor' else 'patient_dashboard'


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(max_length=254)
    subject = forms.CharField(max_length=150)
    message = forms.CharField(max_length=3000, widget=forms.Textarea)


def site_home(request):
    """Public landing page and contact form."""
    form = ContactForm(request.POST or None)
    contact_status = ''
    if request.method == 'POST' and form.is_valid():
        recipient = os.getenv('CONTACT_EMAIL', '').strip()
        if not recipient or not os.getenv('EMAIL_HOST'):
            contact_status = 'unavailable'
        else:
            data = form.cleaned_data
            try:
                EmailMessage(
                    subject=f"Oasis contact: {data['subject']}",
                    body=f"From: {data['name']} <{data['email']}>\n\n{data['message']}",
                    to=[recipient], reply_to=[data['email']],
                ).send(fail_silently=False)
            except Exception:
                logging.getLogger(__name__).exception('Contact form delivery failed')
                contact_status = 'unavailable'
            else:
                return redirect('/?contact=sent#contact')
    elif request.method == 'GET' and request.GET.get('contact') == 'sent':
        contact_status = 'sent'
    return render(request, 'home.html', {'contact_form': form, 'contact_status': contact_status})


def home(request):
    """Fallback for patient navigation links owned by the patient portal."""
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect(_dashboard_for(request.user))


@login_required
def patient_dashboard(request):
    """Render the patient dashboard without redirecting back to itself."""
    if request.user.account_type == 'doctor':
        return redirect('doctor_dashboard')
    return render(request, 'dashboard.html')


@login_required(login_url='login')
def guided_eye_care(request):
    if request.user.account_type == 'doctor':
        return redirect('doctor_dashboard')
    return render(request, 'patient_portal/guided_eye_care.html')


@login_required(login_url='login')
def other_eye_tests(request):
    """Render the patient-facing visual screening library."""
    if request.user.account_type == 'doctor':
        return redirect('doctor_dashboard')
    latest_colour_session = (
        ColourVisionSession.objects.filter(user=request.user)
        .order_by('-updated_at')
        .first()
    )
    marketplace_products = list(
        MarketplaceProduct.objects.filter(is_active=True, stock__gt=0)
        .values('name', 'category', 'short_description')
    )
    doctor_directory = []
    doctors = User.objects.filter(
        account_type=User.AccountType.DOCTOR
    ).select_related('doctor_profile').order_by('first_name', 'last_name', 'username')
    for doctor in doctors:
        profile = getattr(doctor, 'doctor_profile', None)
        name = doctor.get_full_name().strip() or doctor.username
        doctor_directory.append({
            'name': f'Dr. {name}' if not name.lower().startswith('dr.') else name,
            'specialty': (profile.specialty if profile and profile.specialty else 'Eye-care professional'),
            'clinic': (profile.clinic_name if profile and profile.clinic_name else ''),
            'city': (profile.city if profile and profile.city else ''),
        })
    return render(
        request,
        'patient_portal/other_eye_tests.html',
        {
            'latest_colour_session': latest_colour_session,
            'insight_products': marketplace_products,
            'insight_doctors': doctor_directory,
        },
    )


@login_required(login_url='login')
def patient_plan(request):
    """Render the patient's monthly eye-care planning workspace."""
    if request.user.account_type == 'doctor':
        return redirect('doctor_dashboard')
    return render(request, 'patient_portal/plan.html')


def legacy_patient_dashboard(request):
    """Keep historic /dashboard/ links working while using the pt URL."""
    return redirect('patient_dashboard')


@login_required
def patient_profile(request):
    if request.user.account_type == 'doctor':
        return redirect('doctor_profile_settings')
    return render(request, 'patient_portal/profile.html')


@login_required
def patient_profile(request):
    if request.user.account_type == 'doctor':
        return redirect('doctor_profile_settings')
    return render(request, 'patient_portal/profile.html')
