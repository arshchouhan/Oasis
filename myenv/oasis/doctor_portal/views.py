import json
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.shortcuts import redirect, render
from django.urls import reverse
from django.urls import reverse

from patient_portal.models import DirectMessage, DirectMessageThread, User
from patient_portal.visit_models import DoctorConnection, DoctorConnectionRequest
from .models import DoctorProfile, GoogleCalendarConnection, ReferralActivity, ReferralThread, SharedDigitalReport


GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'


def _calendar_token(connection):
    """Return a valid Calendar token, refreshing it when Google permits it."""
    if connection.expires_at > timezone.now() + timedelta(seconds=60):
        return connection.access_token
    if not connection.refresh_token:
        return ''
    token_request = Request(
        'https://oauth2.googleapis.com/token',
        data=urlencode({
            'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'refresh_token': connection.refresh_token,
            'grant_type': 'refresh_token',
        }).encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urlopen(token_request, timeout=10) as response:
            data = json.load(response)
    except Exception:
        return ''
    connection.access_token = data.get('access_token', '')
    connection.expires_at = timezone.now() + timedelta(seconds=int(data.get('expires_in', 3600)))
    connection.save(update_fields=('access_token', 'expires_at', 'updated_at'))
    return connection.access_token


def get_doctor_meet_events(doctor):
    """Read the doctor's upcoming Calendar events that have Google Meet links."""
    connection = GoogleCalendarConnection.objects.filter(user=doctor).first()
    if not connection:
        return [], 'Google Calendar has not been connected by this doctor.'
    token = _calendar_token(connection)
    if not token:
        return [], 'Google Calendar access expired. The doctor needs to reconnect it.'
    query = urlencode({
        'timeMin': timezone.now().isoformat(), 'singleEvents': 'true',
        'orderBy': 'startTime', 'maxResults': 30, 'conferenceDataVersion': 1,
    })
    try:
        request = Request(
            f'https://www.googleapis.com/calendar/v3/calendars/primary/events?{query}',
            headers={'Authorization': f'Bearer {token}'},
        )
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except Exception:
        return [], 'Google Meet details could not be loaded right now.'
    events = []
    for event in payload.get('items', []):
        entries = event.get('conferenceData', {}).get('entryPoints', [])
        meet_url = next((entry.get('uri') for entry in entries if entry.get('entryPointType') == 'video'), event.get('hangoutLink', ''))
        if meet_url:
            events.append({'title': event.get('summary') or 'Google Meet consultation', 'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')), 'meet_url': meet_url})
    events.sort(key=lambda event: event['start'])
    return events, ''


@login_required(login_url='doctor_login')
def dashboard(request):
    """Doctor Portal entry point using the shared ClearEye application shell."""
    if request.user.account_type != User.AccountType.DOCTOR:
        messages.error(request, 'Doctor Portal is available to doctor accounts only.')
        return redirect('patient_dashboard')
    return render(request, 'doctor_portal/dashboard.html', {
        'calendar_connected': GoogleCalendarConnection.objects.filter(user=request.user).exists(),
    })


@login_required(login_url='doctor_login')
def upcoming_meetings(request):
    """Return the signed-in doctor's real, upcoming Google Meet events."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return JsonResponse({'events': [], 'error': 'Doctor Portal access is required.'}, status=403)
    events, error = get_doctor_meet_events(request.user)
    return JsonResponse({'events': events, 'error': error})


@login_required(login_url='doctor_login')
def community(request):
    """Doctor community is a dashboard child, not the dashboard route itself."""
    if request.user.account_type != User.AccountType.DOCTOR:
        messages.error(request, 'Doctor Portal is available to doctor accounts only.')
        return redirect('patient_dashboard')
    return render(request, 'doctor_portal/community.html')


@login_required(login_url='doctor_login')
def connections(request):
    """Doctor-side equivalent of Your Doctor: accepted patients in twin panes."""
    if request.user.account_type != User.AccountType.DOCTOR:
        messages.error(request, 'Doctor Portal is available to doctor accounts only.')
        return redirect('patient_dashboard')
    threads = DirectMessageThread.objects.filter(doctor=request.user).select_related('patient').prefetch_related('messages')
    patients = []
    for thread in threads:
        connection_request = _doctor_thread_request(thread, request.user)
        if connection_request and connection_request.status == DoctorConnectionRequest.Status.ACCEPTED:
            patients.append({
                'patient_id': thread.patient_id,
                'portal_patient_id': thread.patient.patient_id or '',
                'thread_id': thread.id,
                'name': thread.patient.get_full_name() or thread.patient.username,
                'email': thread.patient.email,
                'joined_at': connection_request.responded_at or connection_request.requested_at,
                'message_count': len(thread.messages.all()),
            })

    # A referred patient may not have a direct-message connection with this
    # doctor, so keep received referrals as a separate patient collection.
    referred_patients_by_id = {}
    received_referrals = ReferralThread.objects.filter(
        referred_doctor=request.user,
    ).exclude(
        status=ReferralThread.Status.CLOSED,
    ).select_related('patient', 'referring_doctor').prefetch_related('activities__actor').order_by('-updated_at')
    for referral in received_referrals:
        item = referred_patients_by_id.get(referral.patient_id)
        if item:
            item['referral_count'] += 1
            continue
        referred_patients_by_id[referral.patient_id] = {
            'referral_id': referral.id,
            'referral_activities': list(referral.activities.all()),
            'patient_id': referral.patient_id,
            'name': referral.patient.get_full_name() or referral.patient.username,
            'email': referral.patient.email,
            'referred_at': referral.created_at,
            'referring_doctor': referral.referring_doctor.get_full_name() or referral.referring_doctor.username,
            'referral_type': referral.referral_type,
            'status': referral.get_status_display(),
            'referral_count': 1,
        }
    referred_patients = list(referred_patients_by_id.values())
    return render(request, 'doctor_portal/connections.html', {
        'patients': patients,
        'referred_patients': referred_patients,
    })


@login_required(login_url='doctor_login')
def patient_digital_reports(request, patient_id):
    """Return report snapshots explicitly shared by one accepted patient."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return JsonResponse({'reports': [], 'error': 'Doctor Portal access is required.'}, status=403)
    patient = _care_patient(request.user, patient_id)
    if not patient:
        return JsonResponse({'reports': [], 'error': 'This patient has not granted report access.'}, status=403)
    reports = SharedDigitalReport.objects.filter(doctor=request.user, patient_id=patient_id)
    return JsonResponse({'reports': [{
        'id': report.id,
        'generated_at': timezone.localtime(report.generated_at).strftime('%d %b %Y, %I:%M %p').lstrip('0'),
        'shared_at': timezone.localtime(report.shared_at).strftime('%d %b %Y, %I:%M %p').lstrip('0'),
        'blink_rate': round(report.blink_rate, 1),
        'redness_score': round(report.redness_score, 1),
        'tracking_quality': report.tracking_quality,
    } for report in reports]})


@login_required(login_url='doctor_login')
def reports_workspace(request, patient_id):
    """Dedicated view of digital reports explicitly shared by a connected patient."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    patient = _care_patient(request.user, patient_id)
    if not patient:
        messages.error(request, 'This patient has not granted report access.')
        return redirect('doctor_connections')
    reports = SharedDigitalReport.objects.filter(doctor=request.user, patient_id=patient_id).order_by('-shared_at')
    context = {'patient': patient, 'reports': reports}
    if request.GET.get('panel') == '1':
        return render(request, 'doctor_portal/reports_workspace_panel.html', context)
    return render(request, 'doctor_portal/reports_workspace.html', context)


@login_required(login_url='doctor_login')
def patient_referrals(request, patient_id):
    """List and create referral threads for one of the doctor's patients."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return JsonResponse({'error': 'Doctor Portal access is required.'}, status=403)
    patient = _care_patient(request.user, patient_id)
    if not patient:
        return JsonResponse({'error': 'This patient is not connected to your portal.'}, status=403)
    if request.method == 'POST':
        try:
            referred_doctor_id = int(request.POST.get('doctor_id', ''))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Choose a doctor for the referral.'}, status=400)
        referred_doctor = User.objects.filter(id=referred_doctor_id, account_type=User.AccountType.DOCTOR).exclude(id=request.user.id).first()
        if not referred_doctor:
            return JsonResponse({'error': 'Choose another Oasis doctor for the referral.'}, status=400)
        referral = ReferralThread.objects.create(patient=patient, referring_doctor=request.user, referred_doctor=referred_doctor, note=request.POST.get('note', '').strip()[:2000], referral_type=request.POST.get('referral_type', 'Specialist consultation')[:80], priority=request.POST.get('priority', 'routine')[:16], preferred_date=parse_date(request.POST.get('preferred_date', '')))
        ReferralActivity.objects.create(referral=referral, actor=request.user, action='created', detail='Referral thread started')
    referrals = ReferralThread.objects.filter(patient_id=patient_id, referring_doctor=request.user).select_related('referred_doctor').prefetch_related('activities__actor')
    doctors = User.objects.filter(account_type=User.AccountType.DOCTOR).exclude(id=request.user.id).select_related('doctor_profile').order_by('first_name', 'last_name', 'username')
    return JsonResponse({
        'referrals': [{
            'id': referral.id,
            'doctor_name': f"Dr. {referral.referred_doctor.get_full_name() or referral.referred_doctor.username}",
            'status': referral.get_status_display(),
            'note': referral.note,
            'created_at': timezone.localtime(referral.created_at).strftime('%d %b %Y, %I:%M %p').lstrip('0'),
            'activities': [{
                'action': activity.action,
                'detail': activity.detail,
                'actor': f"Dr. {activity.actor.get_full_name() or activity.actor.username}",
                'at': timezone.localtime(activity.created_at).strftime('%d %b, %I:%M %p').lstrip('0'),
            } for activity in referral.activities.all()],
        } for referral in referrals],
        'doctors': [{
            'id': doctor.id,
            'name': f"Dr. {doctor.get_full_name() or doctor.username}",
            'specialty': getattr(getattr(doctor, 'doctor_profile', None), 'specialty', '') or 'Doctor',
        } for doctor in doctors],
    })


@login_required(login_url='doctor_login')
def referral_workspace(request, patient_id):
    """Dedicated referral page for one accepted patient connection."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    patient = _care_patient(request.user, patient_id)
    if not patient:
        messages.error(request, 'This patient is not connected to your portal.')
        return redirect('doctor_connections')

    doctors = User.objects.filter(account_type=User.AccountType.DOCTOR).exclude(id=request.user.id).select_related('doctor_profile').order_by('first_name', 'last_name', 'username')
    if request.method == 'POST':
        try:
            referred_doctor_id = int(request.POST.get('doctor_id', ''))
        except (TypeError, ValueError):
            referred_doctor_id = 0
        referred_doctor = doctors.filter(id=referred_doctor_id).first()
        note = request.POST.get('note', '').strip()[:2000]
        if not referred_doctor or not note:
            messages.error(request, 'Choose a doctor and enter the reason for referral.')
        else:
            referral = ReferralThread.objects.create(
                patient=patient, referring_doctor=request.user, referred_doctor=referred_doctor,
                note=note, referral_type=request.POST.get('referral_type', 'Specialist consultation')[:80],
                priority=request.POST.get('priority', 'routine')[:16],
                preferred_date=parse_date(request.POST.get('preferred_date', '')),
            )
            ReferralActivity.objects.create(referral=referral, actor=request.user, action='created', detail='Referral thread started')
            messages.success(request, 'Referral thread started.')
            return redirect('doctor_referral_workspace', patient_id=patient_id)

    context = {
        'patient': patient,
        'portal_patient_id': patient.patient_id or '',
        'doctors': doctors,
    }
    if request.GET.get('panel') == '1':
        return render(request, 'doctor_portal/referral_workspace_panel.html', context)
    return render(request, 'doctor_portal/referral_workspace.html', context)


@login_required(login_url='doctor_login')
def referral_manager(request):
    """Manage the signed-in doctor's sent and received referral threads."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return JsonResponse({'error': 'Doctor Portal access is required.'}, status=403)
    if request.method == 'POST':
        try:
            referral_id = int(request.POST.get('referral_id', ''))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Choose a valid referral thread.'}, status=400)
        referral = ReferralThread.objects.filter(id=referral_id, referred_doctor=request.user).first()
        action = request.POST.get('action')
        if not referral or action not in ('accept', 'close'):
            return JsonResponse({'error': 'This referral thread cannot be updated.'}, status=403)
        referral.status = ReferralThread.Status.ACCEPTED if action == 'accept' else ReferralThread.Status.CLOSED
        referral.save(update_fields=('status', 'updated_at'))
        ReferralActivity.objects.create(referral=referral, actor=request.user, action=referral.status, detail=f'Referral {referral.status}')

    def serialize(referral, direction):
        counterpart = referral.referred_doctor if direction == 'sent' else referral.referring_doctor
        return {
            'id': referral.id,
            'direction': direction,
            'patient_name': referral.patient.get_full_name() or referral.patient.username,
            'doctor_name': f"Dr. {counterpart.get_full_name() or counterpart.username}",
            'status': referral.get_status_display(),
            'note': referral.note,
            'updated_at': timezone.localtime(referral.updated_at).strftime('%d %b, %I:%M %p').lstrip('0'),
        }

    sent = ReferralThread.objects.filter(referring_doctor=request.user).select_related('patient', 'referred_doctor')
    received = ReferralThread.objects.filter(referred_doctor=request.user).select_related('patient', 'referring_doctor')
    return JsonResponse({'sent': [serialize(item, 'sent') for item in sent], 'received': [serialize(item, 'received') for item in received]})


def _doctor_thread_request(thread, doctor):
    return DoctorConnectionRequest.objects.filter(
        user=thread.patient,
        recipient_email__iexact=doctor.email,
    ).order_by('-requested_at').first()


@login_required(login_url='doctor_login')
def direct_messages(request, thread_id=None):
    """Doctor-side conversation workspace for patient connection requests."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    threads = DirectMessageThread.objects.filter(doctor=request.user).select_related('patient').prefetch_related('messages__sender')
    thread = threads.filter(id=thread_id).first() if thread_id else threads.first()
    # Keep each patient's latest request beside their conversation so the
    # doctor can make the decision directly from the left-hand list.
    thread_items = [
        {'thread': item, 'connection_request': _doctor_thread_request(item, request.user)}
        for item in threads
    ]
    connection_request = _doctor_thread_request(thread, request.user) if thread else None
    if request.method == 'POST' and thread and connection_request and connection_request.status == DoctorConnectionRequest.Status.ACCEPTED:
        body = request.POST.get('body', '').strip()
        if body:
            DirectMessage.objects.create(thread=thread, sender=request.user, body=body)
            thread.save(update_fields=('updated_at',))
        return redirect('doctor_direct_messages', thread_id=thread.id)
    return render(request, 'doctor_portal/direct_messages.html', {
        'thread_items': thread_items,
        'thread': thread,
        'connection_request': connection_request,
        'single_layout': request.GET.get('layout') == 'single',
    })


@login_required(login_url='doctor_login')
def connection_request_decision(request, thread_id):
    """Accept or decline a patient's Direct Messages connection request."""
    if request.method != 'POST' or request.user.account_type != User.AccountType.DOCTOR:
        return redirect('doctor_connections')
    thread = DirectMessageThread.objects.filter(id=thread_id, doctor=request.user).select_related('patient').first()
    if not thread:
        return redirect('doctor_direct_messages')
    connection_request = _doctor_thread_request(thread, request.user)
    if not connection_request or connection_request.status != DoctorConnectionRequest.Status.PENDING:
        return redirect('doctor_direct_messages', thread_id=thread.id)

    decision = request.POST.get('decision')
    connection_request.status = (
        DoctorConnectionRequest.Status.ACCEPTED if decision == 'accept' else DoctorConnectionRequest.Status.DECLINED
    )
    connection_request.responded_at = timezone.now()
    connection_request.save(update_fields=('status', 'responded_at'))

    if connection_request.status == DoctorConnectionRequest.Status.ACCEPTED:
        profile, _ = DoctorProfile.objects.get_or_create(user=request.user)
        DoctorConnection.objects.update_or_create(
            user=thread.patient,
            doctor_email=request.user.email,
            defaults={
                'doctor_name': f'Dr. {request.user.get_full_name() or request.user.username}',
                'specialty': profile.specialty,
                'clinic_name': profile.clinic_name,
                'clinic_address': profile.city or '',
                'phone': profile.phone or '',
                # Do not invent public ratings, availability, or experience.
                # These remain blank until such doctor information exists.
                'rating': 0,
                'review_count': 0,
                'experience_years': 0,
                'next_available': '',
                'source': 'oasis_doctor_portal',
                'is_demo': False,
            },
        )
    return redirect('doctor_direct_messages', thread_id=thread.id)


@login_required(login_url='doctor_login')
def google_calendar_connect(request):
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        messages.error(request, 'Google Calendar credentials are not configured on this server yet.')
        return redirect('doctor_dashboard')
    state = secrets.token_urlsafe(32)
    request.session['google_calendar_oauth_state'] = state
    callback = request.build_absolute_uri(reverse('doctor_google_calendar_callback'))
    query = urlencode({
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
        'redirect_uri': callback,
        'response_type': 'code',
        'scope': GOOGLE_CALENDAR_SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state,
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{query}')


@login_required(login_url='doctor_login')
def google_calendar_callback(request):
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    expected_state = request.session.pop('google_calendar_oauth_state', '')
    if not expected_state or not secrets.compare_digest(expected_state, request.GET.get('state', '')):
        messages.error(request, 'Google Calendar authorization could not be verified.')
        return redirect('doctor_dashboard')
    if request.GET.get('error') or not request.GET.get('code'):
        messages.error(request, 'Google Calendar authorization was cancelled.')
        return redirect('doctor_dashboard')
    callback = request.build_absolute_uri(reverse('doctor_google_calendar_callback'))
    token_request = Request(
        'https://oauth2.googleapis.com/token',
        data=urlencode({
            'code': request.GET['code'], 'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
            'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
            'redirect_uri': callback, 'grant_type': 'authorization_code',
        }).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urlopen(token_request, timeout=10) as response:
            token = json.load(response)
    except Exception:
        messages.error(request, 'Google Calendar could not complete authorization. Please try again.')
        return redirect('doctor_dashboard')
    existing = GoogleCalendarConnection.objects.filter(user=request.user).first()
    GoogleCalendarConnection.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': token.get('access_token', ''),
            'refresh_token': token.get('refresh_token') or (existing.refresh_token if existing else ''),
            'expires_at': timezone.now() + timedelta(seconds=int(token.get('expires_in', 3600))),
        },
    )
    messages.success(request, 'Google Calendar is connected. Upcoming Google Meet consultations are ready to share.')
    return redirect('doctor_dashboard')


@login_required(login_url='doctor_login')
def google_calendar_disconnect(request):
    if request.method == 'POST' and request.user.account_type == User.AccountType.DOCTOR:
        GoogleCalendarConnection.objects.filter(user=request.user).delete()
    return redirect('doctor_dashboard')


@login_required(login_url='doctor_login')
def google_meet_details(request):
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    return redirect('doctor_dashboard')


@login_required(login_url='doctor_login')
def schedule_google_meet(request, patient_id):
    """Create a Calendar event and ask Google Calendar to generate a Meet link."""
    if request.user.account_type != User.AccountType.DOCTOR or request.method != 'POST':
        return JsonResponse({'error': 'Invalid scheduling request.'}, status=403)
    patient = _care_patient(request.user, patient_id)
    if not patient:
        return JsonResponse({'error': 'This patient is not connected to your portal.'}, status=404)
    connection = GoogleCalendarConnection.objects.filter(user=request.user).first()
    token = _calendar_token(connection) if connection else ''
    if not token:
        return JsonResponse({'error': 'Connect or reconnect Google Calendar before scheduling a Meet.'}, status=400)
    title = request.POST.get('title', '').strip() or f'Consultation with {patient.get_full_name() or patient.username}'
    start = request.POST.get('start', '').strip()
    end = request.POST.get('end', '').strip()
    if not start or not end:
        return JsonResponse({'error': 'Choose both a start and end time.'}, status=400)
    start_value = parse_datetime(start)
    end_value = parse_datetime(end)
    if not start_value or not end_value:
        return JsonResponse({'error': 'Use valid start and end date/time values.'}, status=400)
    if timezone.is_naive(start_value):
        start_value = timezone.make_aware(start_value, timezone.get_current_timezone())
    if timezone.is_naive(end_value):
        end_value = timezone.make_aware(end_value, timezone.get_current_timezone())
    if end_value <= start_value:
        return JsonResponse({'error': 'The meeting end time must be after its start time.'}, status=400)
    event = {
        'summary': title,
        'description': request.POST.get('description', '').strip(),
        'start': {'dateTime': start_value.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end_value.isoformat(), 'timeZone': 'Asia/Kolkata'},
        'attendees': [{'email': patient.email}],
        'conferenceData': {'createRequest': {'requestId': str(uuid.uuid4())}},
    }
    try:
        api_request = Request(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1&sendUpdates=all',
            data=json.dumps(event).encode(),
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(api_request, timeout=15) as response:
            created = json.load(response)
    except HTTPError as error:
        try:
            reason = json.load(error).get('error', {}).get('message', 'Google Calendar rejected the request.')
        except Exception:
            reason = 'Google Calendar rejected the request.'
        return JsonResponse({'error': f'Google Calendar error {error.code}: {reason}'}, status=error.code)
    except Exception:
        return JsonResponse({'error': 'Google Calendar could not schedule the meeting. Reconnect Calendar and try again.'}, status=502)
    entries = created.get('conferenceData', {}).get('entryPoints', [])
    meet_url = next((entry.get('uri') for entry in entries if entry.get('entryPointType') == 'video'), created.get('hangoutLink', ''))
    return JsonResponse({'title': created.get('summary', title), 'meet_url': meet_url, 'start': created.get('start', {}).get('dateTime', start)})


@login_required(login_url='doctor_login')
def meet_workspace(request, patient_id):
    """Standalone Google Meet scheduling page for a connected patient."""
    if request.user.account_type != User.AccountType.DOCTOR:
        return redirect('patient_dashboard')
    patient = _care_patient(request.user, patient_id)
    if not patient:
        messages.error(request, 'This patient is not connected to your portal.')
        return redirect('doctor_connections')
    context = {'patient': patient}
    if request.GET.get('panel') == '1':
        return render(request, 'doctor_portal/meet_workspace_panel.html', context)
    return render(request, 'doctor_portal/meet_workspace.html', context)


def _care_patient(doctor, patient_id):
    """Resolve a primary patient or an active referral received by this doctor."""
    if doctor.account_type != User.AccountType.DOCTOR:
        return None
    patient = User.objects.filter(id=patient_id, account_type=User.AccountType.PATIENT).first()
    if not patient:
        return None
    thread = DirectMessageThread.objects.filter(doctor=doctor, patient=patient).first()
    connection = _doctor_thread_request(thread, doctor) if thread else None
    if connection and connection.status == DoctorConnectionRequest.Status.ACCEPTED:
        return patient
    if ReferralThread.objects.filter(
        referred_doctor=doctor, patient=patient,
        status__in=(ReferralThread.Status.OPEN, ReferralThread.Status.ACCEPTED),
    ).exists():
        return patient
    return None


def home(request):
    """Doctor portal entry point with a doctor-only authentication flow."""
    if not request.user.is_authenticated:
        return redirect('doctor_login')
    return redirect('doctor_dashboard' if request.user.account_type == User.AccountType.DOCTOR else 'patient_dashboard')


@login_required(login_url='doctor_login')
def profile(request):
    """Edit professional information inside the doctor portal workspace."""
    if request.user.account_type != User.AccountType.DOCTOR:
        messages.error(request, 'Doctor Portal is available to doctor accounts only.')
        return redirect('patient_dashboard')

    profile_record, _ = DoctorProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save(update_fields=['first_name', 'last_name'])

        profile_record.specialty = request.POST.get('specialty', '').strip()
        profile_record.registration_number = request.POST.get('registration_number', '').strip()
        profile_record.clinic_name = request.POST.get('clinic_name', '').strip()
        profile_record.city = request.POST.get('city', '').strip()
        profile_record.phone = request.POST.get('phone', '').strip()
        profile_record.biography = request.POST.get('biography', '').strip()
        profile_record.save()
        messages.success(request, 'Your doctor profile has been saved.')
        return redirect('doctor_profile')

    return render(request, 'doctor_portal/profile.html', {'profile_record': profile_record})
