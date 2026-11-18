import os
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock

import cv2
import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .image_analysis import ai_report, quality_report
from .models import EyeImageReview


class ImageReviewTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = get_user_model().objects.create_user(username='reviewer', email='review@example.com', password='testpass')
        self.client.force_login(self.user)
        self.data = cv2.imencode('.png', np.full((500, 600, 3), 120, dtype=np.uint8))[1].tobytes()

    def upload(self):
        return self.client.post(reverse('save_eye_image_review'), {'images': SimpleUploadedFile('eye.png', self.data, content_type='image/png')})

    def test_upload_quality_and_missing_ai_key_are_persisted(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        review = EyeImageReview.objects.get()
        self.assertEqual(review.analysis['quality']['width'], 600)
        self.assertEqual(review.analysis['image_type'], 'Unverified')
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            response = self.client.post(reverse('analyse_eye_image_review', args=[review.pk]))
        self.assertEqual(response.json()['analysis']['status'], 'not_configured')
        review.refresh_from_db()
        self.assertEqual(review.analysis['status'], 'not_configured')

    def test_invalid_image_rejects_entire_batch(self):
        response = self.client.post(reverse('save_eye_image_review'), {'images': [
            SimpleUploadedFile('eye.png', self.data, content_type='image/png'),
            SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')]})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EyeImageReview.objects.exists())

    def test_other_account_cannot_analyse_image(self):
        self.upload()
        other = get_user_model().objects.create_user(username='other', email='other@example.com')
        self.client.force_login(other)
        with patch('patient_portal.symptom_views.ai_report') as provider:
            response = self.client.post(reverse('analyse_eye_image_review', args=[EyeImageReview.objects.get().pk]))
            self.assertEqual(response.status_code, 404)
            provider.assert_not_called()

    def test_ai_classifies_unrelated_image_without_inventing_findings(self):
        draft = {'summary': 'Not an eye image.', 'image_type': 'Not an eye image', 'extracted_text': '',
                 'observations': [], 'limitations': ['No eye is visible.'], 'next_steps': ['Upload an eye photo.']}
        import json
        response = Mock()
        response.json.return_value = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(draft)}]}]}
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), patch('patient_portal.image_analysis.requests.post', return_value=response) as post:
            report = ai_report(self.data, quality_report(self.data))
        self.assertEqual(report['status'], 'unsupported')
        self.assertEqual(report['observations'], [])
        self.assertFalse(post.call_args.kwargs['json']['store'])

    def test_provider_failure_is_retryable(self):
        self.upload()
        review = EyeImageReview.objects.get()
        with patch('patient_portal.symptom_views.ai_report', side_effect=ValueError('provider failed')):
            response = self.client.post(reverse('analyse_eye_image_review', args=[review.pk]))
        self.assertEqual(response.json()['analysis']['status'], 'failed')
        self.assertIn('quality', response.json()['analysis'])

    def test_local_model_result_saved_for_owner_only(self):
        import json
        self.upload()
        review = EyeImageReview.objects.get()
        url = reverse('save_local_image_review', args=[review.pk])
        response = self.client.post(url, data=json.dumps({'face_detected': True}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.analysis['status'], 'local_review')
        self.assertEqual(review.analysis['model'], 'MediaPipe Face Landmarker')
        invalid = self.client.post(url, data=json.dumps({'face_detected': 'yes'}), content_type='application/json')
        self.assertEqual(invalid.status_code, 400)
        other = get_user_model().objects.create_user(username='other-local', email='other-local@example.com')
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, data=json.dumps({'face_detected': False}), content_type='application/json').status_code, 404)

    def test_chat_access_and_missing_configuration(self):
        import json
        self.upload()
        url = reverse('image_review_chat', args=[EyeImageReview.objects.get().pk])
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            response = self.client.post(url, data=json.dumps({'question': 'Explain this review'}), content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertIn('not connected', response.json()['error'])
        other = get_user_model().objects.create_user(username='chat-other', email='chat-other@example.com')
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, data=json.dumps({'question': 'Hello'}), content_type='application/json').status_code, 404)
