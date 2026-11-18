import json

import cv2
import numpy as np
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class EyeSpacingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='spacing', email='spacing@example.com', password='test')
        self.client.force_login(self.user)
        frame = np.zeros((400, 600, 3), dtype=np.uint8)
        cv2.rectangle(frame, (100, 100), (400, 280), (255, 255, 255), 3)
        self.data = cv2.imencode('.jpg', frame)[1].tobytes()
        self.url = reverse('estimate_eye_spacing')

    def post_measurement(self, points):
        return self.client.post(self.url, {'frame': SimpleUploadedFile('frame.jpg', self.data, content_type='image/jpeg'), 'points': json.dumps(points)})

    def test_calibrates_using_reference_and_pupil_distance(self):
        response = self.post_measurement([[100, 100], [400, 100], [140, 200], [350, 200]])
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.json()['spacing_mm'], 59.9, places=1)

    def test_unclear_edges_warn_and_outside_frame_is_rejected(self):
        response = self.post_measurement([[150, 150], [350, 150], [140, 200], [300, 200]])
        self.assertEqual(response.status_code, 200)
        self.assertIn('not clear', response.json()['warning'])
        self.assertEqual(self.post_measurement([[100, 100], [700, 100], [140, 200], [350, 200]]).status_code, 400)

    def test_small_card_has_specific_error(self):
        response = self.post_measurement([[100, 100], [110, 100], [140, 200], [350, 200]])
        self.assertEqual(response.status_code, 400)
        self.assertIn('card is too small', response.json()['error'])

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.post_measurement([[100, 100], [400, 100], [140, 200], [350, 200]]).status_code, 401)
