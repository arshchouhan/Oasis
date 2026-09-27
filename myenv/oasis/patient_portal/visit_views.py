from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from .visit_models import DoctorConnection, DoctorConnectionRequest
from .models import DirectMessage, DirectMessageThread, DoctorDirectorySearch, User
from .symptom_models import EyeScan
from doctor_portal.models import SharedDigitalReport


DEMO_DOCTOR_PROFILES = (
    {
        'doctor_name': 'Dr. Aanya Mehta', 'specialty': 'Ophthalmology · Dry eye care',
        'clinic_name': 'VisionPoint Eye Clinic', 'clinic_address': 'Medical Centre, near your area',
        'phone': '+91 98765 21040', 'rating': 4.8, 'review_count': 186,
        'experience_years': 11, 'next_available': 'Tomorrow · 10:30 AM',
    },
    {
        'doctor_name': 'Dr. Rohan Kapoor', 'specialty': 'Ophthalmology · Retina care',
        'clinic_name': 'ClearSight Eye Centre', 'clinic_address': 'Health Plaza, near your area',
        'phone': '+91 98765 21058', 'rating': 4.7, 'review_count': 142,
        'experience_years': 9, 'next_available': 'Thursday · 2:15 PM',
    },
    {
        'doctor_name': 'Dr. Isha Nair', 'specialty': 'Ophthalmology · Cornea care',
        'clinic_name': 'Nayan Eye Institute', 'clinic_address': 'Care Avenue, near your area',
        'phone': '+91 98765 21072', 'rating': 4.9, 'review_count': 221,
        'experience_years': 14, 'next_available': 'Friday · 11:00 AM',
    },
)


@login_required
@require_GET
def doctor_directory(request):
    """Small, patient-facing doctor directory for the navbar quick search."""
    query = request.GET.get('q', '').strip()
    # Do not reveal/list the directory until the patient intentionally starts
    # a search. Each non-empty query is retained as patient search history.
    if not query:
        return JsonResponse({'results': []})
    DoctorDirectorySearch.objects.update_or_create(user=request.user, query=query[:120])
    doctors = User.objects.filter(account_type=User.AccountType.DOCTOR).select_related('doctor_profile')
    doctors = doctors.filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(username__icontains=query)
        | Q(email__icontains=query)
    )

    results = []
    for doctor in doctors.order_by('first_name', 'last_name', 'username')[:8]:
        profile = getattr(doctor, 'doctor_profile', None)
        full_name = doctor.get_full_name().strip() or doctor.username
        results.append({
            'id': doctor.id,
            'name': f'Dr. {full_name}' if not full_name.lower().startswith('dr.') else full_name,
            'email': doctor.email,
            'specialty': profile.specialty if profile and profile.specialty else 'Doctor',
            'clinic': profile.clinic_name if profile and profile.clinic_name else '',
        })
    return JsonResponse({'results': results})


def _send_doctor_connection_request(request, doctor):
    """Create one pending consent request and email its secure approval URL."""
    lookup = _connection_filter(request)
    connection_request = DoctorConnectionRequest.objects.filter(
        **lookup,
        recipient_email=doctor.email,
        status=DoctorConnectionRequest.Status.PENDING,
    ).first()
    if connection_request:
        return connection_request, False

    connection_request = DoctorConnectionRequest.objects.create(
        **_connection_owner_values(request), recipient_email=doctor.email,
    )
    approval_url = request.build_absolute_uri(reverse('doctor_connection_response', args=[connection_request.token]))
    subject = 'Oasis: connection request from a patient'
    body = (
        f'Hello {doctor.get_full_name() or doctor.username},\n\n'
        f'{_request_owner_label(request)} would like to connect with you through Oasis Direct Messages. '
        'No medical records are shared until you approve the request.\n\n'
        f'Review the connection request here:\n{approval_url}\n\nOasis'
    )
    try:
        EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [doctor.email]).send()
    except Exception:
        # The connection remains visible in Doctor Portal even if local SMTP
        # is unavailable, so it can still be approved there.
        pass
    return connection_request, True


@login_required
def direct_message_start(request):
    """Start a patient-to-doctor thread and submit the doctor connection request."""
    if request.method != 'POST' or request.user.account_type != User.AccountType.PATIENT:
        return redirect('doctor_search')
    doctor = User.objects.filter(id=request.POST.get('doctor_id'), account_type=User.AccountType.DOCTOR).first()
    if not doctor:
        messages.error(request, 'Choose a valid doctor before starting a conversation.')
        return redirect('doctor_search')
    thread, _ = DirectMessageThread.objects.get_or_create(patient=request.user, doctor=doctor)
    _send_doctor_connection_request(request, doctor)
    return redirect('direct_messages', thread_id=thread.id)


@login_required
def direct_messages(request, thread_id=None):
    """Patient Direct Messages workspace, with split and single-pane layouts."""
    if request.user.account_type != User.AccountType.PATIENT:
        return redirect('doctor_dashboard')
    threads = DirectMessageThread.objects.filter(patient=request.user).select_related('doctor').prefetch_related('messages__sender')
    thread = threads.filter(id=thread_id).first() if thread_id else threads.first()
    connection_request = None
    if thread:
        connection_request = DoctorConnectionRequest.objects.filter(
            user=request.user,
            recipient_email__iexact=thread.doctor.email,
        ).order_by('-requested_at').first()
    if request.method == 'POST' and thread:
        body = request.POST.get('body', '').strip()
        if body:
            DirectMessage.objects.create(thread=thread, sender=request.user, body=body)
            thread.save(update_fields=('updated_at',))
        return redirect('direct_messages', thread_id=thread.id)
    return render(request, 'patient_portal/visits/direct_messages.html', {
        'threads': threads,
        'thread': thread,
        'connection_request': connection_request,
        'single_layout': request.GET.get('layout') == 'single',
    })


@require_GET
@login_required
def direct_message_updates(request, thread_id):
    """Return new messages for the signed-in patient's open conversation."""
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'messages': []}, status=403)
    thread = DirectMessageThread.objects.filter(id=thread_id, patient=request.user).first()
    if not thread:
        return JsonResponse({'messages': []}, status=404)
    try:
        after_id = max(0, int(request.GET.get('after', '0')))
    except (TypeError, ValueError):
        after_id = 0
    new_messages = thread.messages.filter(id__gt=after_id).select_related('sender')
    return JsonResponse({'messages': [
        {
            'id': message.id,
            'body': message.body,
            'sender_id': message.sender_id,
            'created_at': timezone.localtime(message.created_at).strftime('%d %b, %I:%M %p').lstrip('0'),
        }
        for message in new_messages
    ]})


@login_required
def digital_reports(request):
    """List and share generated eye reports with one accepted Oasis doctor."""
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'error': 'Patient Portal access is required.'}, status=403)
    try:
        connection_id = int(request.GET.get('connection', request.POST.get('connection', '')))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Choose a valid connected doctor.'}, status=400)
    connection = DoctorConnection.objects.filter(id=connection_id, user=request.user, source='oasis_doctor_portal').first()
    doctor = User.objects.filter(account_type=User.AccountType.DOCTOR, email__iexact=connection.doctor_email).first() if connection else None
    accepted = doctor and DoctorConnectionRequest.objects.filter(user=request.user, recipient_email__iexact=doctor.email, status=DoctorConnectionRequest.Status.ACCEPTED).exists()
    if not accepted:
        return JsonResponse({'error': 'This report can only be shared with an accepted doctor connection.'}, status=403)
    if request.method == 'POST':
        try:
            scan_id = int(request.POST.get('scan_id', ''))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Choose a generated report to share.'}, status=400)
        scan = EyeScan.objects.filter(id=scan_id, user=request.user).first()
        if not scan:
            return JsonResponse({'error': 'That generated report is unavailable.'}, status=404)
        SharedDigitalReport.objects.get_or_create(
            patient=request.user, doctor=doctor, source_scan_id=scan.id,
            defaults={'generated_at': scan.created_at, 'blink_rate': scan.blink_rate, 'redness_score': scan.redness_score, 'tracking_quality': scan.tracking_quality},
        )
    shared_ids = set(SharedDigitalReport.objects.filter(patient=request.user, doctor=doctor).values_list('source_scan_id', flat=True))
    reports = [{
        'id': scan.id,
        'created_at': timezone.localtime(scan.created_at).strftime('%d %b %Y, %I:%M %p').lstrip('0'),
        'blink_rate': round(scan.blink_rate, 1),
        'redness_score': round(scan.redness_score, 1),
        'tracking_quality': scan.tracking_quality,
        'shared': scan.id in shared_ids,
    } for scan in EyeScan.objects.filter(user=request.user).order_by('-created_at')]
    return JsonResponse({'reports': reports})


def _connection_filter(request):
    if request.user.is_authenticated:
        return {'user': request.user}
    if not request.session.session_key:
        request.session.create()
    return {'user__isnull': True, 'session_key': request.session.session_key}


def _connection_owner_values(request):
    """Concrete values suitable for creating a connection/request record."""
    if request.user.is_authenticated:
        return {'user': request.user, 'session_key': ''}
    if not request.session.session_key:
        request.session.create()
    return {'user': None, 'session_key': request.session.session_key}


def _demo_profile_for(email):
    return DEMO_DOCTOR_PROFILES[sum(ord(char) for char in email.lower()) % len(DEMO_DOCTOR_PROFILES)]


def _request_owner_label(request):
    if request.user.is_authenticated:
        return request.user.get_full_name() or request.user.username or 'a ClearEye client'
    return 'a ClearEye client'


def _request_lookup_from_record(connection_request):
    if connection_request.user_id:
        return {'user_id': connection_request.user_id, 'session_key': ''}
    return {'user': None, 'session_key': connection_request.session_key}


def get_visits_context():
    upcoming_visits = [
        {
            'id': 1,
            'doctor_name': 'Dr. Sarah Jenkins',
            'title': 'Ophthalmologist (Cornea Specialist)',
            'clinic': 'ClearEye Vision Institute',
            'date': '24 Sep 2026',
            'time': '10:30 AM',
            'status': 'Confirmed',
            'type': 'In-Person',
            'icon': 'stethoscope',
            'reason': 'Dry Eye Follow-up & Tear Film Analysis',
            'location': 'Suite 402, Medical Center'
        },
        {
            'id': 2,
            'doctor_name': 'Dr. Marcus Vance',
            'title': 'Optometrist & Ocular Surface Specialist',
            'clinic': 'Metro Eye Care Center',
            'date': '05 Oct 2026',
            'time': '02:15 PM',
            'status': 'Pending',
            'type': 'Virtual Consult',
            'icon': 'videocam',
            'reason': 'Routine Prescription & Screen Strain Check',
            'location': 'Online Video Call'
        }
    ]

    past_visits = [
        {
            'id': 101,
            'doctor_name': 'Dr. Sarah Jenkins',
            'title': 'Ophthalmologist',
            'date': '12 Aug 2026',
            'diagnosis': 'Mild Ocular Surface Dryness',
            'notes': 'Prescribed lubricating drops 3x daily. Tear film breakup time: 7s.',
            'status': 'Completed',
            'icon': 'check_circle'
        },
        {
            'id': 102,
            'doctor_name': 'Dr. Elena Rostova',
            'title': 'Corneal Specialist',
            'date': '14 May 2026',
            'diagnosis': 'Seasonal Allergic Conjunctivitis',
            'notes': 'Antihistamine drops prescribed for 14 days. Symptoms resolved.',
            'status': 'Completed',
            'icon': 'check_circle'
        }
    ]

    doctors = [
        {
            'name': 'Dr. Sarah Jenkins',
            'specialty': 'Cornea & Refractive Surgery',
            'rating': '4.9 ★ (128 reviews)',
            'experience': '12 yrs exp',
            'available': 'Next available: Tomorrow 10:30 AM',
            'icon': 'person'
        },
        {
            'name': 'Dr. Marcus Vance',
            'specialty': 'Dry Eye & Ocular Surface',
            'rating': '4.8 ★ (94 reviews)',
            'experience': '9 yrs exp',
            'available': 'Next available: Thursday 2:15 PM',
            'icon': 'person'
        },
        {
            'name': 'Dr. Elena Rostova',
            'specialty': 'General Ophthalmology',
            'rating': '4.9 ★ (210 reviews)',
            'experience': '15 yrs exp',
            'available': 'Next available: Friday 11:00 AM',
            'icon': 'person'
        }
    ]

    return {
        'upcoming_visits': upcoming_visits,
        'past_visits': past_visits,
        'doctors': doctors,
    }


def visits_home(request):
    """Connect and show the user's doctor profile."""
    lookup = _connection_filter(request)
    connected_doctors = list(DoctorConnection.objects.filter(**lookup))
    connected_doctor = connected_doctors[0] if connected_doctors else None
    show_connection_form = not bool(connected_doctor)

    # A Doctor Portal profile is the source of truth. Refresh the patient's
    # saved view whenever the doctor has completed more of their profile.
    if connected_doctor and connected_doctor.source == 'oasis_doctor_portal':
        doctor_user = User.objects.filter(
            email__iexact=connected_doctor.doctor_email,
            account_type=User.AccountType.DOCTOR,
        ).select_related('doctor_profile').first()
        if doctor_user:
            profile = getattr(doctor_user, 'doctor_profile', None)
            values = {
                'doctor_name': f'Dr. {doctor_user.get_full_name() or doctor_user.username}',
                'specialty': profile.specialty if profile else '',
                'clinic_name': profile.clinic_name if profile else '',
                'clinic_address': profile.city if profile else '',
                'phone': profile.phone if profile else '',
                'rating': 0,
                'review_count': 0,
                'experience_years': 0,
                'next_available': '',
            }
            if any(getattr(connected_doctor, field) != value for field, value in values.items()):
                for field, value in values.items():
                    setattr(connected_doctor, field, value)
                connected_doctor.save(update_fields=[*values.keys(), 'updated_at'])

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'disconnect' and connected_doctor:
            connected_doctor.delete()
            return redirect('find_doctor')

        email = request.POST.get('doctor_email', '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            pass
        else:
            DoctorConnectionRequest.objects.filter(
                **lookup,
                recipient_email=email,
                status=DoctorConnectionRequest.Status.PENDING,
            ).delete()
            connection_request = DoctorConnectionRequest.objects.create(
                **_connection_owner_values(request),
                recipient_email=email,
            )
            approval_url = request.build_absolute_uri(
                reverse('doctor_connection_response', args=[connection_request.token])
            )
            subject = 'ClearEye: connection request from a client'
            body = (
                f'Hello,\n\n{_request_owner_label(request)} has asked to connect your provider profile '
                'to ClearEye. This does not share medical records.\n\n'
                f'To review and approve the connection, open this secure link:\n{approval_url}\n\n'
                'If you were not expecting this request, you can ignore this email.\n\nClearEye'
            )
            email_message = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [email])
            try:
                delivered = email_message.send()
            except Exception:
                connection_request.delete()
            else:
                if not delivered:
                    connection_request.delete()

        connected_doctor = DoctorConnection.objects.filter(**lookup).first()
        show_connection_form = not bool(connected_doctor)

    return render(request, 'patient_portal/visits/find_doctor.html', {
        'active_subpage': 'find_doctor',
        'connected_doctor': connected_doctor,
        'show_connection_form': show_connection_form,
    })


def doctor_connection_response(request, token):
    """Doctor-facing consent page reached through the emailed approval link."""
    connection_request = DoctorConnectionRequest.objects.filter(token=token).first()
    if not connection_request:
        return render(request, 'patient_portal/visits/doctor_connection_response.html', {'invalid_request': True}, status=404)

    if request.method == 'POST' and connection_request.status == DoctorConnectionRequest.Status.PENDING:
        decision = request.POST.get('decision')
        connection_request.status = (
            DoctorConnectionRequest.Status.ACCEPTED
            if decision == 'accept' else DoctorConnectionRequest.Status.DECLINED
        )
        connection_request.responded_at = timezone.now()
        connection_request.save(update_fields=('status', 'responded_at'))

        if connection_request.status == DoctorConnectionRequest.Status.ACCEPTED:
            profile = _demo_profile_for(connection_request.recipient_email)
            DoctorConnection.objects.update_or_create(
                **_request_lookup_from_record(connection_request),
                defaults={
                    **profile,
                    'doctor_email': connection_request.recipient_email,
                    'source': 'demo_provider_directory',
                    'is_demo': True,
                },
            )

    return render(request, 'patient_portal/visits/doctor_connection_response.html', {
        'connection_request': connection_request,
        'invalid_request': False,
    })


def my_appointments(request):
    """Render My Appointments page with separate twin-pane workspace and dashboard layout."""
    context = get_visits_context()
    context['active_subpage'] = 'my_appointments'
    return render(request, 'patient_portal/visits/my_appointments.html', context)


def doctor_search(request):
    """Show the saved doctor in the existing two-sibling profile workspace."""
    lookup = _connection_filter(request)
    connected_doctors = list(DoctorConnection.objects.filter(**lookup))
    connected_doctor = connected_doctors[0] if connected_doctors else None
    request_just_sent = request.GET.get('request') == 'sent'

    for connection in connected_doctors:
        if connection.source != 'oasis_doctor_portal':
            continue
        doctor_user = User.objects.filter(email__iexact=connection.doctor_email, account_type=User.AccountType.DOCTOR).select_related('doctor_profile').first()
        if doctor_user:
            profile = getattr(doctor_user, 'doctor_profile', None)
            values = {'doctor_name': f'Dr. {doctor_user.get_full_name() or doctor_user.username}', 'specialty': profile.specialty if profile else '', 'clinic_name': profile.clinic_name if profile else '', 'clinic_address': profile.city if profile else '', 'phone': profile.phone if profile else '', 'rating': 0, 'review_count': 0, 'experience_years': 0, 'next_available': ''}
            for field, value in values.items():
                setattr(connection, field, value)
            connection.save(update_fields=[*values.keys(), 'updated_at'])

    pending_request = None
    if not connected_doctor:
        pending_request = DoctorConnectionRequest.objects.filter(
            **lookup,
            status=DoctorConnectionRequest.Status.PENDING,
        ).order_by('-requested_at').first()

    if connected_doctors:
        doctors = [{
            'connection_id': connection.id, 'name': connection.doctor_name,
            'specialty': connection.specialty, 'rating': '', 'experience': '', 'available': '',
            'clinic_name': connection.clinic_name, 'clinic_address': connection.clinic_address,
            'phone': connection.phone, 'email': connection.doctor_email, 'source': connection.source,
            'icon': 'person',
        } for connection in connected_doctors]
    else:
        email = pending_request.recipient_email if pending_request else 'doctor@clinic.com'
        profile = _demo_profile_for(email)
        doctors = [{
            'name': profile['doctor_name'],
            'specialty': profile['specialty'],
            'rating': f"{profile['rating']} ★ ({profile['review_count']} reviews)",
            'experience': f"{profile['experience_years']} yrs exp",
            'available': f"Next available: {profile['next_available']}",
            'icon': 'person',
        }]
        connected_doctor = type('PendingConnection', (), {
            'clinic_name': profile['clinic_name'],
            'clinic_address': profile['clinic_address'],
            'doctor_email': email,
        })()

    context = {
        'doctors': doctors,
        'query': '',
        'selected_doctor': doctors[0],
        'connected_doctor': connected_doctor,
    }
    return render(request, 'patient_portal/visits/doctor_search.html', context)


@login_required
def patient_google_meet(request):
    """Show real-time Meet events only for the patient's accepted doctor."""
    if request.user.account_type != User.AccountType.PATIENT:
        return redirect('doctor_dashboard')
    connection = DoctorConnection.objects.filter(user=request.user, source='oasis_doctor_portal')
    if request.GET.get('connection'):
        connection = connection.filter(id=request.GET.get('connection'))
    connection = connection.first()
    if not connection:
        messages.error(request, 'Connect with a Doctor Portal doctor before viewing Meet details.')
        return redirect('doctor_search')
    doctor = User.objects.filter(email__iexact=connection.doctor_email, account_type=User.AccountType.DOCTOR).first()
    if not doctor:
        messages.error(request, 'This doctor is no longer available.')
        return redirect('doctor_search')
    from doctor_portal.views import get_doctor_meet_events
    events, notice = get_doctor_meet_events(doctor)
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'doctor_name': doctor.get_full_name() or doctor.username,
            'notice': notice,
            'events': events,
        })
    return render(request, 'patient_portal/visits/google_meet.html', {
        'doctor': doctor, 'events': events, 'notice': notice,
    })
