import json
from datetime import datetime, timedelta
from decimal import Decimal

import razorpay
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from .visit_models import ConsultationSessionRequest, DoctorConnection, DoctorConnectionRequest
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


SESSION_DURATION_FEES = {
    60: Decimal('100.00'),
    120: Decimal('1500.00'),
    180: Decimal('4000.00'),
}


def _razorpay_configured():
    return settings.RAZORPAY_KEY_ID.startswith('rzp_test_') and bool(settings.RAZORPAY_KEY_SECRET)


def _session_connection(request, connection_id):
    connection = get_object_or_404(
        DoctorConnection,
        pk=connection_id,
        user=request.user,
        source='oasis_doctor_portal',
    )
    doctor = User.objects.filter(
        email__iexact=connection.doctor_email,
        account_type=User.AccountType.DOCTOR,
    ).first()
    if not doctor:
        return connection, None
    return connection, doctor


@login_required
def session_request(request, connection_id):
    """Show the paid follow-up request form for one connected doctor."""
    if request.user.account_type != User.AccountType.PATIENT:
        return redirect('doctor_dashboard')
    connection, doctor = _session_connection(request, connection_id)
    if not doctor:
        messages.error(request, 'This doctor is no longer available for session requests.')
        return redirect('doctor_search')
    submitted_request = None
    submitted_id = request.GET.get('submitted')
    if submitted_id and submitted_id.isdigit():
        submitted_request = ConsultationSessionRequest.objects.filter(
            pk=int(submitted_id), patient=request.user, doctor_connection_id=connection.pk,
            status=ConsultationSessionRequest.Status.REQUESTED,
        ).first()
    return render(request, 'patient_portal/visits/session_request.html', {
        'connection': connection,
        'doctor': doctor,
        'duration_fees': SESSION_DURATION_FEES,
        'submitted_request': submitted_request,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'available_times': [
            {'start': window.starts_at, 'minutes': (window.ends_at - window.starts_at) // timedelta(minutes=1)}
            for window in doctor.availability_windows.filter(starts_at__gt=timezone.now())
        ],
        'availability_timezone': timezone.get_current_timezone_name(),
    })


def _parse_preferred_datetime(value):
    try:
        scheduled = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if timezone.is_naive(scheduled):
        scheduled = timezone.make_aware(scheduled, timezone.get_current_timezone())
    return scheduled


@login_required
@require_POST
def create_session_request_order(request):
    """Create an amount-validated Razorpay order for a consultation request."""
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'error': 'A patient account is required.'}, status=403)
    if not _razorpay_configured():
        return JsonResponse({'error': 'Razorpay test keys are not configured on the server.'}, status=503)
    try:
        connection_id = int(request.POST.get('connection_id', ''))
        duration = int(request.POST.get('duration_minutes', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Choose a valid session duration.'}, status=400)
    fee = SESSION_DURATION_FEES.get(duration)
    preferred_datetime = _parse_preferred_datetime(request.POST.get('preferred_datetime', ''))
    reason = request.POST.get('reason', '').strip()
    notes = request.POST.get('notes', '').strip()
    if not fee:
        return JsonResponse({'error': 'Choose one of the available session durations.'}, status=400)
    if not preferred_datetime or preferred_datetime <= timezone.now():
        return JsonResponse({'error': 'Choose a preferred date and time in the future.'}, status=400)
    if not reason:
        return JsonResponse({'error': 'Tell your doctor what you would like to discuss.'}, status=400)
    if len(reason) > 240 or len(notes) > 2000:
        return JsonResponse({'error': 'Please shorten the reason or notes and try again.'}, status=400)
    connection, doctor = _session_connection(request, connection_id)
    if not doctor:
        return JsonResponse({'error': 'This doctor is no longer available for session requests.'}, status=404)
    window = doctor.availability_windows.filter(starts_at=preferred_datetime).first()
    if not window or window.ends_at - window.starts_at < timedelta(minutes=duration):
        return JsonResponse({'error': 'That time is unavailable for this session length. Refresh and choose another time.'}, status=400)
    session_request = ConsultationSessionRequest.objects.create(
        patient=request.user,
        doctor=doctor,
        doctor_connection_id=connection.pk,
        duration_minutes=duration,
        amount=fee,
        preferred_datetime=preferred_datetime,
        reason=reason,
        notes=notes,
    )
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order = client.order.create({
            'amount': int(fee * 100),
            'currency': 'INR',
            'receipt': f'oasis_session_{session_request.pk}_{timezone.now():%m%d%H%M%S}',
            'notes': {
                'session_request_id': str(session_request.pk),
                'patient_id': str(request.user.pk),
                'doctor_id': str(doctor.pk),
                'duration_minutes': str(duration),
            },
        })
    except razorpay.errors.BadRequestError:
        session_request.delete()
        return JsonResponse({'error': 'Razorpay could not create the payment order. Please try again.'}, status=502)
    session_request.razorpay_order_id = order['id']
    session_request.save(update_fields=('razorpay_order_id', 'updated_at'))
    return JsonResponse({
        'request_id': session_request.pk,
        'key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],
        'amount': order['amount'],
        'currency': order['currency'],
        'description': f'{duration // 60}-hour session with Dr. {doctor.get_full_name() or doctor.username}',
    })


@login_required
@require_POST
def verify_session_request_payment(request):
    """Verify Razorpay's signature and only then mark the request as paid."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
        request_id = int(payload.get('request_id'))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'error': 'The payment response was invalid.'}, status=400)
    session_request = get_object_or_404(ConsultationSessionRequest, pk=request_id, patient=request.user)
    if session_request.payment_verified_at or session_request.status == ConsultationSessionRequest.Status.REQUESTED:
        return JsonResponse({'redirect_url': f"{reverse('session_request', args=[session_request.doctor_connection_id])}?submitted={session_request.pk}"})
    if payload.get('razorpay_order_id') != session_request.razorpay_order_id:
        return JsonResponse({'error': 'The payment order does not match this request.'}, status=400)
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_payment_signature({
            'razorpay_payment_id': payload.get('razorpay_payment_id', ''),
            'razorpay_order_id': payload.get('razorpay_order_id', ''),
            'razorpay_signature': payload.get('razorpay_signature', ''),
        })
        order = client.order.fetch(session_request.razorpay_order_id)
        if order.get('currency') != 'INR' or int(order.get('amount', 0)) != int(session_request.amount * 100):
            raise ValueError('Payment amount mismatch.')
    except (razorpay.errors.SignatureVerificationError, razorpay.errors.BadRequestError, ValueError):
        return JsonResponse({'error': 'We could not verify that payment. No session request was submitted.'}, status=400)
    now = timezone.now()
    ConsultationSessionRequest.objects.filter(pk=session_request.pk, status=ConsultationSessionRequest.Status.PAYMENT_PENDING).update(
        status=ConsultationSessionRequest.Status.REQUESTED,
        razorpay_payment_id=payload['razorpay_payment_id'],
        payment_verified_at=now,
        updated_at=now,
    )
    return JsonResponse({'redirect_url': f"{reverse('session_request', args=[session_request.doctor_connection_id])}?submitted={session_request.pk}"})


@login_required
@require_GET
def your_requests(request):
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'error': 'A patient account is required.'}, status=403)
    connections = {
        connection.doctor_email.casefold(): connection.pk
        for connection in DoctorConnection.objects.filter(
            user=request.user, source='oasis_doctor_portal',
        )
    }
    profiles = {
        connection.doctor_email.casefold(): connection.pk
        for connection in DoctorConnection.objects.filter(user=request.user)
    }
    connection_requests = DoctorConnectionRequest.objects.filter(user=request.user)
    for item in connection_requests:
        if item.status == DoctorConnectionRequest.Status.ACCEPTED:
            item.profile_connection_id = profiles.get(item.recipient_email.casefold())
    consultation_requests = ConsultationSessionRequest.objects.filter(
        patient=request.user,
    ).select_related('doctor').order_by('-created_at')
    for item in consultation_requests:
        item.video_connection_id = connections.get(item.doctor.email.casefold())
    return render(request, 'patient_portal/visits/your_requests.html', {
        'connection_requests': connection_requests,
        'consultation_requests': consultation_requests,
    })


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
    if request.method == 'POST' and thread and connection_request and connection_request.status == DoctorConnectionRequest.Status.ACCEPTED:
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
        SharedDigitalReport.objects.update_or_create(
            patient=request.user, doctor=doctor, source_scan_id=scan.id,
            defaults={'generated_at': scan.created_at, 'blink_rate': scan.blink_rate, 'redness_score': scan.redness_score, 'tracking_quality': scan.tracking_quality,
                      'assessment_details': {field: getattr(scan, field) for field in ('duration_seconds', 'blink_count', 'complete_blink_count', 'incomplete_blink_rate', 'average_interblink_interval', 'average_blink_duration', 'average_eye_opening', 'left_ear', 'right_ear', 'redness_index', 'sampled_frames')}},
        )
    shared_ids = set(SharedDigitalReport.objects.filter(patient=request.user, doctor=doctor).values_list('source_scan_id', flat=True))
    reports = [{
        'id': scan.id,
        'created_at': timezone.localtime(scan.created_at).strftime('%d %b %Y, %I:%M %p').lstrip('0'),
        'blink_rate': round(scan.blink_rate, 1),
        'redness_score': round(scan.redness_score, 1),
        'tracking_quality': scan.tracking_quality,
        'shared': scan.id in shared_ids,
        'details': {field: getattr(scan, field) for field in ('duration_seconds', 'blink_count', 'complete_blink_count', 'incomplete_blink_rate', 'average_interblink_interval', 'average_blink_duration', 'average_eye_opening', 'left_ear', 'right_ear', 'redness_index', 'sampled_frames')},
    } for scan in EyeScan.objects.filter(user=request.user).order_by('-created_at')]
    return JsonResponse({'reports': reports, 'patient_name': request.user.get_full_name() or request.user.username, 'patient_id': request.user.patient_id, 'doctor_name': doctor.get_full_name() or doctor.username})


@login_required
@require_GET
def consultation_history(request):
    from django.shortcuts import get_object_or_404
    if request.GET.get('referral', '').isdigit():
        from doctor_portal.models import ReferralThread
        from types import SimpleNamespace
        referral = get_object_or_404(ReferralThread.objects.exclude(status='closed'), pk=request.GET['referral'], patient=request.user)
        profile = getattr(referral.referred_doctor, 'doctor_profile', None)
        connection = SimpleNamespace(doctor_email=referral.referred_doctor.email, doctor_name=referral.referred_doctor.get_full_name() or referral.referred_doctor.username, specialty=profile.specialty if profile else '')
    else:
        connection = get_object_or_404(DoctorConnection, pk=request.GET.get('connection') if request.GET.get('connection', '').isdigit() else 0, user=request.user)
    doctor = User.objects.filter(email__iexact=connection.doctor_email, account_type=User.AccountType.DOCTOR).first()
    thread = DirectMessageThread.objects.filter(patient=request.user, doctor=doctor).first() if doctor else None
    notes = [{'date': message.created_at.isoformat(), 'body': message.body} for message in DirectMessage.objects.filter(thread=thread, sender=doctor).order_by('-created_at')] if thread else []
    meetings, notice = [], ''
    from doctor_portal.models import ConsultationRecord
    consultations = [{'id':record.pk,'date':record.consulted_at.isoformat(),'notes':record.notes,'prescription':record.prescription,'follow_up':record.follow_up} for record in ConsultationRecord.objects.filter(patient=request.user,doctor=doctor)] if doctor else []
    if doctor:
        from doctor_portal.views import get_doctor_meet_events
        meetings, notice = get_doctor_meet_events(doctor, patient=request.user, history=True)
    return JsonResponse({
        'doctor_name': connection.doctor_name, 'specialty': connection.specialty,
        'doctor_messages': notes,
        'message_url': reverse('direct_messages', args=[thread.pk]) if thread else reverse('direct_messages'),
        'prescriptions': [], 'follow_up': [],
        'meetings': meetings, 'notice': notice,
        'consultations': consultations,
    })


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
    """Keep old bookmarks working after retiring the appointments page."""
    return redirect('doctor_search')


def doctor_search(request):
    """Show the saved doctor in the existing two-sibling profile workspace."""
    lookup = _connection_filter(request)
    connected_doctors = list(DoctorConnection.objects.filter(**lookup))
    connected_doctor = connected_doctors[0] if connected_doctors else None

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

    doctors = [{
        'connection_id': connection.id, 'name': connection.doctor_name,
        'specialty': connection.specialty, 'rating': '', 'experience': '', 'available': '',
        'clinic_name': connection.clinic_name, 'clinic_address': connection.clinic_address,
        'phone': connection.phone, 'email': connection.doctor_email, 'source': connection.source,
        'icon': 'person',
    } for connection in connected_doctors]

    from doctor_portal.models import ReferralThread
    for doc in doctors:
        doc['group'] = 'primary'
    if request.user.is_authenticated:
        seen = set()
        for referral in ReferralThread.objects.filter(patient=request.user).exclude(status='closed').select_related('referred_doctor__doctor_profile', 'referring_doctor'):
            if referral.referred_doctor_id in seen:
                continue
            seen.add(referral.referred_doctor_id)
            user = referral.referred_doctor
            profile = getattr(user, 'doctor_profile', None)
            doctors.append({'name':f'Dr. {user.get_full_name() or user.username}', 'specialty':profile.specialty if profile else '', 'clinic_name':profile.clinic_name if profile else '', 'clinic_address':profile.city if profile else '', 'phone':profile.phone if profile else '', 'email':user.email, 'source':'referral', 'group':'referred', 'referral_id':referral.pk, 'referring_name':referral.referring_doctor.get_full_name() or referral.referring_doctor.username, 'referring_doctor_id':referral.referring_doctor.doctor_id, 'referral_type':referral.referral_type, 'referral_status':referral.get_status_display(), 'icon':'person'})
    for doc in doctors:
        doctor_user = User.objects.filter(email__iexact=doc.get('email', ''), account_type=User.AccountType.DOCTOR).first() if doc.get('email') else None
        if doctor_user:
            doc['doctor_id'] = doctor_user.pk
            doc['portal_doctor_id'] = doctor_user.doctor_id
            doc['profile_image_url'] = doctor_user.profile_image_url
            doc['availability_windows'] = doctor_user.availability_windows.filter(starts_at__gt=timezone.now())[:5]
            thread = DirectMessageThread.objects.filter(patient=request.user, doctor=doctor_user).first() if request.user.is_authenticated else None
            doc['message_url'] = reverse('direct_messages', args=[thread.pk]) if thread else ''
    context = {
        'doctors': doctors,
        'query': '',
        'connected_doctor': connected_doctor,
        'availability_timezone': timezone.get_current_timezone_name(),
    }
    return render(request, 'patient_portal/visits/doctor_search.html', context)


@login_required
def upcoming_meetings(request):
    """List only consultations inviting the signed-in patient."""
    if request.user.account_type != User.AccountType.PATIENT:
        return JsonResponse({'error': 'Patient account required.'}, status=403)
    from doctor_portal.views import get_doctor_meet_events
    from doctor_portal.models import ReferralThread
    emails = set(DoctorConnection.objects.filter(user=request.user, source='oasis_doctor_portal').values_list('doctor_email', flat=True))
    emails.update(ReferralThread.objects.filter(patient=request.user).exclude(status='closed').values_list('referred_doctor__email', flat=True))
    events, notices, seen = [], [], set()
    for email in emails:
        doctor = User.objects.filter(email__iexact=email, account_type=User.AccountType.DOCTOR).first()
        if not doctor:
            continue
        meetings, notice = get_doctor_meet_events(doctor, patient=request.user)
        if notice:
            notices.append(notice)
        for meeting in meetings:
            key = (meeting['meet_url'], meeting['start'])
            if key not in seen:
                seen.add(key)
                events.append(meeting)
    events.sort(key=lambda meeting: meeting['start'])
    return JsonResponse({'events': events, 'notice': ' '.join(dict.fromkeys(notices))})


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
    events, notice = get_doctor_meet_events(doctor, patient=request.user)
    if request.GET.get('format') == 'json':
        return JsonResponse({
            'doctor_name': doctor.get_full_name() or doctor.username,
            'notice': notice,
            'events': events,
            'request_session_url': reverse('session_request', args=[connection.pk]),
        })
    return render(request, 'patient_portal/visits/google_meet.html', {
        'doctor': doctor, 'events': events, 'notice': notice,
    })
