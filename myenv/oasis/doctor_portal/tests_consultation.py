from django.test import TestCase
from django.urls import reverse
from patient_portal.models import User, DirectMessageThread
from patient_portal.visit_models import DoctorConnectionRequest, DoctorConnection
from .models import ConsultationRecord
from unittest.mock import patch
from types import SimpleNamespace


class ConsultationTests(TestCase):
    def setUp(self):
        self.doctor=User.objects.create_user(username='doc',email='doc@example.com',account_type='doctor')
        self.patient=User.objects.create_user(username='pat',email='pat@example.com')
        DirectMessageThread.objects.create(doctor=self.doctor,patient=self.patient)
        # Connection tables are missing from this repository's test migrations.
        self.connection=SimpleNamespace(pk=1,doctor_email=self.doctor.email,doctor_name='Doctor',specialty='Eye care')
        self.care_patch=patch('doctor_portal.views._care_patient',side_effect=lambda doctor,patient_id:self.patient if doctor==self.doctor and patient_id==self.patient.pk else None)
        self.care_patch.start()
        self.addCleanup(self.care_patch.stop)

    def test_save_and_patient_history(self):
        self.client.force_login(self.doctor)
        url=reverse('doctor_consultation_workspace',args=[self.patient.pk])
        self.assertContains(self.client.get(url),'Save consultation')
        self.assertEqual(self.client.post(url,{'consulted_at':'2026-10-02T17:30','notes':'Review discussion','prescription':'Recorded prescription','follow_up':'Review in two weeks'}).status_code,200)
        self.assertEqual(ConsultationRecord.objects.get().doctor,self.doctor)
        self.client.force_login(self.patient)
        with patch('doctor_portal.views.get_doctor_meet_events',return_value=([],'')), patch('django.shortcuts.get_object_or_404',return_value=self.connection):
            response=self.client.get(reverse('consultation_history'),{'connection':self.connection.pk})
        self.assertEqual(response.json()['consultations'][0]['prescription'],'Recorded prescription')
        self.assertEqual(self.client.post(url,{'notes':'Unauthorized'}).status_code,403)

    def test_unconnected_doctor_and_validation(self):
        self.client.force_login(self.doctor)
        url=reverse('doctor_consultation_workspace',args=[self.patient.pk])
        self.assertEqual(self.client.post(url,{'consulted_at':'invalid','notes':''}).status_code,400)
        self.assertFalse(ConsultationRecord.objects.exists())
        other=User.objects.create_user(username='other',email='other@example.com',account_type='doctor')
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code,403)
