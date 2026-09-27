from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """Application user stored in SQLite through Django's normal ORM."""

    class AccountType(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        DOCTOR = 'doctor', 'Doctor'

    email = models.EmailField('email address', unique=True)
    account_type = models.CharField(
        max_length=12,
        choices=AccountType.choices,
        default=AccountType.PATIENT,
        help_text='Determines the dashboard available after login.',
    )
    patient_id = models.CharField(max_length=16, unique=True, null=True, blank=True, editable=False)
    doctor_id = models.CharField(max_length=16, unique=True, null=True, blank=True, editable=False)
    google_sub = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text='Google OpenID Connect subject identifier.',
    )

    class Meta:
        ordering = ('date_joined',)

    def __str__(self):
        return self.email or self.username

    def save(self, *args, **kwargs):
        """Assign a stable, human-readable portal ID when an account is created."""
        if self.account_type == self.AccountType.PATIENT and not self.patient_id:
            self.patient_id = f'PAT-{uuid.uuid4().hex[:10].upper()}'
        elif self.account_type == self.AccountType.DOCTOR and not self.doctor_id:
            self.doctor_id = f'DR-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)


class DoctorDirectorySearch(models.Model):
    """A patient's real doctor-directory searches, retained in SQLite."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_directory_searches')
    query = models.CharField(max_length=120)
    searched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-searched_at',)
        constraints = [models.UniqueConstraint(fields=('user', 'query'), name='unique_patient_doctor_search')]


class DirectMessageThread(models.Model):
    """A patient's private conversation request with one doctor account."""

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='direct_message_threads')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_message_threads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)
        constraints = [models.UniqueConstraint(fields=('patient', 'doctor'), name='unique_patient_doctor_thread')]


class DirectMessage(models.Model):
    thread = models.ForeignKey(DirectMessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_direct_messages')
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)


class PatientTaskList(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_lists')
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ('id',)


class PatientTask(models.Model):
    task_list = models.ForeignKey(PatientTaskList, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    notes = models.TextField(blank=True, max_length=5000)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ('completed', '-id')


class PatientNote(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_notes')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, max_length=5000)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)


from .symptom_models import EyeScan  # noqa: E402,F401
from .visit_models import DoctorConnection, DoctorConnectionRequest  # noqa: E402,F401
