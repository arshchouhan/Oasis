import os
import uuid
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import EyeScan
from .video_analysis import analyse_recording


def symptom_tracker(request):
    """Render the Symptom Tracker / Eye Scanner page."""
    scan = EyeScan.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    redness_score = scan.redness_score if scan else 0
    blink_rate = scan.blink_rate if scan else 0
    tracking_quality = scan.tracking_quality if scan else 0
    demo_scan_results = [
        {'label': 'Blink rate', 'score': round(blink_rate, 1), 'max': 30, 'severity': 'Good' if 10 <= blink_rate <= 25 else 'Review', 'icon': 'motion_photos_on'},
        {'label': 'Blinks', 'score': scan.blink_count if scan else 0, 'max': 30, 'severity': 'Measured', 'icon': 'visibility'},
        {'label': 'Visual redness', 'score': round(redness_score, 1), 'max': 10, 'severity': 'Estimate', 'icon': 'remove_red_eye'},
        {'label': 'Tracking quality', 'score': tracking_quality, 'max': 100, 'severity': 'Good' if tracking_quality >= 70 else 'Review', 'icon': 'center_focus_strong'},
    ]

    demo_analysis_categories = [
        {'name': 'Redness Detection', 'icon': 'remove_red_eye', 'status': 'Moderate', 'color': '#2E7D8A'},
        {'name': 'Dryness Indicators', 'icon': 'water_drop', 'status': 'Elevated', 'color': '#1D61AC'},
        {'name': 'Surface Appearance', 'icon': 'visibility', 'status': 'Normal', 'color': '#006A6A'},
        {'name': 'Blink Quality', 'icon': 'motion_photos_on', 'status': 'Good', 'color': '#006A6A'},
        {'name': 'Tear Film Indicators', 'icon': 'opacity', 'status': 'Moderate', 'color': '#2E7D8A'},
    ]

    captures = []
    if scan:
            captures = [
                {'eye': 'Left Eye', 'image_url': scan.left_image_url, 'time': scan.created_at},
                {'eye': 'Right Eye', 'image_url': scan.right_image_url, 'time': scan.created_at},
            ]

    demo_history = [
        {'date': 'Today', 'time': '10:24 AM', 'eye': 'Left Eye', 'redness': 3.8, 'change': '+12%', 'direction': 'up'},
        {'date': 'Yesterday', 'time': '9:10 PM', 'eye': 'Left Eye', 'redness': 3.2, 'change': '-8%', 'direction': 'down'},
        {'date': '15 Sep', 'time': '8:15 AM', 'eye': 'Right Eye', 'redness': 4.1, 'change': None, 'direction': None},
    ]

    context = {
        'scan_results': demo_scan_results,
        'analysis_categories': demo_analysis_categories,
        'captures': captures,
        'history': demo_history,
        'assessment': scan,
    }
    return render(request, 'patient_portal/symptoms/tracker.html', context)


@require_POST
def save_eye_scan(request):
    """Upload a one-minute assessment recording and its eye previews to Cloudinary."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Please log in before saving an eye scan.'}, status=401)

    left_image = request.FILES.get('left_image')
    right_image = request.FILES.get('right_image')
    recording = request.FILES.get('recording')
    if not left_image or not right_image or not recording:
        return JsonResponse({'error': 'Recording and both eye previews are required.'}, status=400)

    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    api_key = os.getenv('CLOUDINARY_API_KEY', '')
    api_secret = os.getenv('CLOUDINARY_API_SECRET', '')
    if not all((cloud_name, api_key, api_secret)) and os.getenv('CLOUDINARY_URL'):
        credentials = urlparse(os.getenv('CLOUDINARY_URL', ''))
        cloud_name = cloud_name or credentials.hostname or ''
        api_key = api_key or unquote(credentials.username or '')
        api_secret = api_secret or unquote(credentials.password or '')
    try:
        folder = f'oasis/eye-scans/{request.user.pk}'
        if all((cloud_name, api_key, api_secret)):
            import cloudinary
            import cloudinary.uploader
            cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
            left_upload = cloudinary.uploader.upload(left_image, folder=folder, resource_type='image')
            right_upload = cloudinary.uploader.upload(right_image, folder=folder, resource_type='image')
            recording_upload = cloudinary.uploader.upload(recording, folder=folder, resource_type='video')
            try:
                video_measurements = analyse_recording(recording_upload['secure_url'])
            except Exception:
                video_measurements = {'duration_seconds': 0, 'tracking_quality': 0, 'redness_score': None, 'sampled_frames': 0}
        else:
            # Self-hosted fallback: an optional Cloudinary account must not
            # prevent a patient from completing an assessment.
            token = uuid.uuid4().hex
            left_name = default_storage.save(f'{folder}/{token}-left.jpg', left_image)
            right_name = default_storage.save(f'{folder}/{token}-right.jpg', right_image)
            recording_name = default_storage.save(f'{folder}/{token}-assessment.webm', recording)
            left_upload = {'secure_url': default_storage.url(left_name), 'public_id': left_name}
            right_upload = {'secure_url': default_storage.url(right_name), 'public_id': right_name}
            recording_upload = {'secure_url': default_storage.url(recording_name), 'public_id': recording_name}
            video_measurements = {'duration_seconds': 0, 'tracking_quality': 0, 'redness_score': None, 'sampled_frames': 0}
        duration = min(60, max(1, video_measurements['duration_seconds']))
        if not video_measurements['duration_seconds']:
            duration = min(60, max(1, int(request.POST.get('duration_seconds', 60))))
        blink_count = min(300, max(0, int(request.POST.get('blink_count', 0))))
        blink_rate = min(120, max(0, float(request.POST.get('blink_rate', 0))))
        incomplete_blink_rate = min(100, max(0, float(request.POST.get('incomplete_blink_rate', 0))))
        complete_blink_count = min(blink_count, max(0, int(request.POST.get('complete_blink_count', blink_count))))
        average_interblink_interval = min(60, max(0, float(request.POST.get('average_interblink_interval', 0))))
        average_blink_duration = min(2000, max(0, float(request.POST.get('average_blink_duration', 0))))
        average_eye_opening = min(1, max(0, float(request.POST.get('average_eye_opening', 0))))
        left_ear = min(1, max(0, float(request.POST.get('left_ear', 0))))
        right_ear = min(1, max(0, float(request.POST.get('right_ear', 0))))
        client_tracking_quality = min(100, max(0, int(request.POST.get('tracking_quality', 0))))
        client_redness_score = min(10, max(0, float(request.POST.get('redness_score', 0))))
        tracking_quality = video_measurements['tracking_quality'] or client_tracking_quality
        redness_score = video_measurements['redness_score'] if video_measurements['redness_score'] is not None else client_redness_score
        redness_index = round(redness_score / 10, 3)
        sampled_frames = video_measurements['sampled_frames']
        scan = EyeScan.objects.filter(user=request.user).first()
        if scan is None:
            scan = EyeScan.objects.create(
                user=request.user,
                left_image_url=left_upload['secure_url'],
                right_image_url=right_upload['secure_url'],
                left_public_id=left_upload.get('public_id', ''),
                right_public_id=right_upload.get('public_id', ''),
                recording_url=recording_upload['secure_url'],
                recording_public_id=recording_upload.get('public_id', ''),
                duration_seconds=duration,
                blink_count=blink_count,
                blink_rate=blink_rate,
                incomplete_blink_rate=incomplete_blink_rate,
                complete_blink_count=complete_blink_count,
                average_interblink_interval=average_interblink_interval,
                average_blink_duration=average_blink_duration,
                average_eye_opening=average_eye_opening,
                left_ear=left_ear,
                right_ear=right_ear,
                redness_index=redness_index,
                tracking_quality=tracking_quality,
                redness_score=redness_score,
                sampled_frames=sampled_frames,
            )
        else:
            scan.left_image_url = left_upload['secure_url']
            scan.right_image_url = right_upload['secure_url']
            scan.left_public_id = left_upload.get('public_id', '')
            scan.right_public_id = right_upload.get('public_id', '')
            scan.recording_url = recording_upload['secure_url']
            scan.recording_public_id = recording_upload.get('public_id', '')
            scan.duration_seconds = duration
            scan.blink_count = blink_count
            scan.blink_rate = blink_rate
            scan.incomplete_blink_rate = incomplete_blink_rate
            scan.complete_blink_count = complete_blink_count
            scan.average_interblink_interval = average_interblink_interval
            scan.average_blink_duration = average_blink_duration
            scan.average_eye_opening = average_eye_opening
            scan.left_ear = left_ear
            scan.right_ear = right_ear
            scan.redness_index = redness_index
            scan.tracking_quality = tracking_quality
            scan.redness_score = redness_score
            scan.sampled_frames = sampled_frames
            scan.created_at = timezone.now()
            scan.save()
            # Keep one current scan record per user for the dashboard pair.
            EyeScan.objects.filter(user=request.user).exclude(pk=scan.pk).delete()
    except Exception:
        return JsonResponse({'error': 'Unable to save the eye images. Please try again.'}, status=502)

    return JsonResponse({
        'id': scan.pk,
        'left_image_url': scan.left_image_url,
        'right_image_url': scan.right_image_url,
        'recording_url': scan.recording_url,
    }, status=201)


def symptom_report(request):
    assessment = EyeScan.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    return render(request, 'patient_portal/symptoms/report_siblings.html', {'assessment': assessment})
