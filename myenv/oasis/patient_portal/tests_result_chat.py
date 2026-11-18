import json
import os
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import ColourVisionSession


class ResultInsightChatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='chat-patient', email='chat-patient@example.com', password='test')
        self.client.force_login(self.user)
        self.session = ColourVisionSession.objects.create(user=self.user, status=ColourVisionSession.Status.ENDED, current_plate=0, correct_answers=0, responses=[])
        self.url = reverse('result_insight_chat')

    def ask(self, **data):
        return self.client.post(self.url, data=json.dumps(data), content_type='application/json')

    def test_partial_saved_session_is_used_and_no_identity_is_sent(self):
        provider = Mock(status_code=200)
        provider.json.return_value = {'candidates': [{'content': {'parts': [{'text': 'The activity was incomplete.'}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}), patch('patient_portal.other_test_views.requests.post', return_value=provider) as post:
            response = self.ask(question='What next?', result_key='colour', session_id=self.session.pk, history=[])
        self.assertEqual(response.status_code, 200)
        self.assertIn('incomplete', response.json()['answer'])
        payload = post.call_args.kwargs['json']
        instruction = payload['systemInstruction']['parts'][0]['text']
        self.assertIn('"status": "ended"', instruction)
        self.assertIn('"responses_recorded": 0', instruction)
        self.assertNotIn(self.user.email, instruction)
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], 'test-key')

    def test_missing_key_and_session_ownership(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            response = self.ask(question='What next?', result_key='colour', session_id=self.session.pk)
        self.assertEqual(response.status_code, 503)
        other = get_user_model().objects.create_user(username='other-chat', email='other-chat@example.com')
        self.client.force_login(other)
        with patch('patient_portal.other_test_views.requests.post') as provider:
            response = self.ask(question='What next?', result_key='colour', session_id=self.session.pk)
        self.assertEqual(response.status_code, 404)
        provider.assert_not_called()

    def test_rejects_invalid_input_and_handles_quota(self):
        self.assertEqual(self.ask(question='', result_key='colour').status_code, 400)
        provider = Mock(status_code=429)
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}), patch('patient_portal.other_test_views.requests.post', return_value=provider):
            self.assertEqual(self.ask(question='Hello', result_key='colour', session_id=self.session.pk).status_code, 429)

    def test_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.ask(question='Hello', result_key='colour').status_code, 401)
