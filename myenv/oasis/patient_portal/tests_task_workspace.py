import json

from django.test import Client, TestCase
from django.urls import reverse

from .models import PatientNote, PatientTask, PatientTaskList, User


class PersonalWorkspaceTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(username='patient', email='patient@example.test')
        self.other = User.objects.create_user(username='other', email='other@example.test')
        self.client.force_login(self.patient)
        self.url = reverse('patient_personal_workspace')

    def post(self, **payload):
        return self.client.post(self.url, json.dumps(payload), content_type='application/json')

    def test_task_and_note_lifecycle(self):
        response = self.post(action='create_list', name='Daily care')
        self.assertEqual(response.status_code, 200)
        list_id = response.json()['lists'][0]['id']
        response = self.post(action='save_task', list_id=list_id, title='Check in', notes='Morning observation', due_date='2026-10-01')
        task_id = response.json()['tasks'][0]['id']
        self.post(action='complete_task', id=task_id, completed=True)
        self.assertTrue(PatientTask.objects.get(id=task_id).completed)
        self.post(action='save_task', id=task_id, title='Updated', notes='New note', due_date='')
        self.assertEqual(PatientTask.objects.get(id=task_id).notes, 'New note')
        response = self.post(action='save_note', title='Observation', body='Personal note')
        note_id = response.json()['notes'][0]['id']
        self.post(action='save_note', id=note_id, title='Edited', body='Updated note')
        self.assertEqual(self.client.get(self.url).json()['notes'][0]['body'], 'Updated note')
        self.post(action='delete_note', id=note_id)
        self.post(action='delete_task', id=task_id)
        self.assertFalse(PatientNote.objects.exists())
        self.assertFalse(PatientTask.objects.exists())

    def test_other_patient_data_is_inaccessible(self):
        other_list = PatientTaskList.objects.create(owner=self.other, name='Private')
        other_task = PatientTask.objects.create(task_list=other_list, title='Secret task')
        other_note = PatientNote.objects.create(owner=self.other, title='Secret note')
        response = self.client.get(self.url)
        self.assertEqual(response.json(), {'lists': [], 'tasks': [], 'notes': []})
        for payload in (
            {'action': 'save_task', 'list_id': other_list.id, 'title': 'Bad'},
            {'action': 'save_task', 'id': other_task.id, 'title': 'Bad'},
            {'action': 'complete_task', 'id': other_task.id, 'completed': True},
            {'action': 'delete_task', 'id': other_task.id},
            {'action': 'save_note', 'id': other_note.id, 'title': 'Bad'},
            {'action': 'delete_note', 'id': other_note.id},
        ):
            self.assertEqual(self.post(**payload).status_code, 400)
        other_task.refresh_from_db()
        self.assertEqual(other_task.title, 'Secret task')

    def test_validation_and_access(self):
        self.assertEqual(self.post(action='create_list', name=' ').status_code, 400)
        self.assertEqual(self.post(action='save_note', title='x'*201).status_code, 400)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.patient)
        self.assertEqual(csrf_client.post(self.url, {'action': 'create_list'}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)
        doctor = User.objects.create_user(username='doctor', email='doctor@example.test', account_type='doctor')
        self.client.force_login(doctor)
        self.assertEqual(self.client.get(self.url).status_code, 403)
