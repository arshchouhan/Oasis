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
    profile_image_url = models.URLField(max_length=1000, blank=True)
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


class ColourVisionSession(models.Model):
    """A resumable, patient-owned colour-plate activity."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        ENDED = 'ended', 'Ended early'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='colour_vision_sessions')
    current_plate = models.PositiveSmallIntegerField(default=0)
    correct_answers = models.PositiveSmallIntegerField(default=0)
    elapsed_seconds = models.PositiveIntegerField(default=0)
    responses = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-updated_at',)


class MarketplaceProduct(models.Model):
    """A clinician-neutral eye-care product shown in the patient marketplace."""

    class Category(models.TextChoices):
        SCREEN_COMFORT = 'screen_comfort', 'Screen comfort'
        DRY_EYE = 'dry_eye', 'Dry-eye support'
        LENS_CARE = 'lens_care', 'Lens care'
        PROTECTION = 'protection', 'Eye protection'
        EVERYDAY = 'everyday', 'Everyday care'

    name = models.CharField(max_length=140)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    short_description = models.CharField(max_length=220)
    details = models.TextField(max_length=1200)
    image_path = models.CharField(max_length=220, help_text='Path relative to the static directory.')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    badge = models.CharField(max_length=48, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-is_featured', 'category', 'name')

    def __str__(self):
        return self.name


class MarketplaceCartItem(models.Model):
    """A patient-owned marketplace basket that persists between visits."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='marketplace_cart_items')
    product = models.ForeignKey(MarketplaceProduct, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveSmallIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)
        constraints = [models.UniqueConstraint(fields=('user', 'product'), name='unique_marketplace_cart_item')]


from .symptom_models import EyeImageReview, EyeScan  # noqa: E402,F401
from .visit_models import ConsultationSessionRequest, DoctorConnection, DoctorConnectionRequest  # noqa: E402,F401
