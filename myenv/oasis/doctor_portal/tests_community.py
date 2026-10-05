from django.test import TestCase, Client
from django.urls import reverse
from patient_portal.models import User
from .models import CommunityPost, CommunityReply
import base64
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile
from .community_forms import CommunityPostForm


class CommunityTests(TestCase):
    def test_media_upload_and_render(self):
        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.client.force_login(self.patient)
            image = SimpleUploadedFile('photo.png', base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='), content_type='image/png')
            url = reverse('patient_community')
            response = self.client.post(url + '?view=create', {'action': 'post', 'title': 'Photo post', 'body': 'My photo', 'topic': 'general', 'media': image})
            self.assertRedirects(response, url)
            post = CommunityPost.objects.get()
            self.assertEqual(post.media_type, 'image')
            self.assertTrue(post.media.storage.exists(post.media.name))
            self.assertContains(self.client.get(url), post.media.url)

    def test_media_validation(self):
        data = {'title': 'Upload', 'body': 'Test', 'topic': 'general'}
        for upload in (SimpleUploadedFile('fake.png', b'not an image'), SimpleUploadedFile('large.mp4', b'x' * (20 * 1024 * 1024 + 1))):
            form = CommunityPostForm(data, {'media': upload})
            self.assertFalse(form.is_valid())
            self.assertIn('media', form.errors)

    @classmethod
    def setUpTestData(cls):
        cls.doctor = User.objects.create_user(username='doctor', email='doctor@example.com', account_type='doctor')
        cls.patient = User.objects.create_user(username='patient', email='patient@example.com', account_type='patient')

    def test_shared_participation_and_owner_permissions(self):
        doctor_url, patient_url = reverse('doctor_community'), reverse('patient_community')
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.post(doctor_url, {'action': 'post', 'title': 'Eye care tips', 'body': '<script>alert(1)</script>', 'topic': 'eye_care'}).status_code, 302)
        post = CommunityPost.objects.get()
        self.client.force_login(self.patient)
        for url in (doctor_url, patient_url):
            response = self.client.get(url)
            self.assertContains(response, 'Eye care tips')
            self.assertContains(response, '&lt;script&gt;')
        self.assertEqual(self.client.post(patient_url, {'action': 'reply', 'post_id': post.pk, 'body': 'Thank you!'}).status_code, 302)
        self.assertEqual(CommunityReply.objects.get().author, self.patient)
        self.client.post(patient_url, {'action': 'like', 'post_id': post.pk})
        self.assertTrue(post.likes.filter(pk=self.patient.pk).exists())
        self.assertContains(self.client.get(patient_url), 'Liked')
        self.client.post(patient_url, {'action': 'like', 'post_id': post.pk})
        self.assertFalse(post.likes.exists())
        self.assertEqual(self.client.post(patient_url, {'action': 'delete_post', 'post_id': post.pk}).status_code, 403)
        self.client.force_login(self.doctor)
        reply = CommunityReply.objects.get()
        self.assertEqual(self.client.post(doctor_url, {'action': 'delete_reply', 'reply_id': reply.pk}).status_code, 404)
        self.client.post(doctor_url, {'action': 'delete_post', 'post_id': post.pk})
        self.assertFalse(CommunityPost.objects.exists())
        self.assertFalse(CommunityReply.objects.exists())

    def test_validation_filters_and_patient_posts(self):
        self.client.force_login(self.patient)
        url = reverse('patient_community')
        for body in ('   ', 'x' * 5001):
            self.assertEqual(self.client.post(url, {'action': 'post', 'title': 'Hello', 'body': body, 'topic': 'general'}).status_code, 200)
        self.assertFalse(CommunityPost.objects.exists())
        self.client.post(url, {'action': 'post', 'title': 'My question', 'body': 'A question', 'topic': 'questions'})
        self.assertContains(self.client.get(url, {'q': 'question', 'topic': 'questions', 'mine': '1'}), 'My question')
        self.assertNotContains(self.client.get(url, {'q': 'unmatched'}), 'My question')
        post = CommunityPost.objects.get()
        self.client.post(url, {'action': 'reply', 'post_id': post.pk, 'body': ' '})
        self.assertFalse(CommunityReply.objects.exists())
        self.assertEqual(self.client.post(url, {'action': 'like', 'post_id': 'invalid'}).status_code, 404)

    def test_authentication_and_csrf(self):
        url = reverse('doctor_community')
        self.assertEqual(self.client.get(url).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.doctor)
        self.assertEqual(client.post(url, {'action': 'post'}).status_code, 403)

    def test_pagination(self):
        CommunityPost.objects.bulk_create([CommunityPost(author=self.doctor, title=f'Post {i}', body='Hello') for i in range(12)])
        self.client.force_login(self.patient)
        response = self.client.get(reverse('patient_community'))
        self.assertEqual(len(response.context['page_obj']), 10)
        self.assertContains(response, 'Next')
