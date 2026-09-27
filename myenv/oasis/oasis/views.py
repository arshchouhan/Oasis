from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required


def _dashboard_for(user):
    return 'doctor_dashboard' if user.account_type == 'doctor' else 'patient_dashboard'


def site_home(request):
    """Reserved public landing page at the site root."""
    return render(request, 'home.html')


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


def legacy_patient_dashboard(request):
    """Keep historic /dashboard/ links working while using the pt URL."""
    return redirect('patient_dashboard')
