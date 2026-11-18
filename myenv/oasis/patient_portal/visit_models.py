from django.conf import settings
from django.db import models
import uuid


class DoctorConnection(models.Model):
    """A user's saved provider connection.

    The current product uses generated demo profiles.  Keeping the provider
    identifier and source here means a verified provider API can replace that
    source later without changing the Visits UI.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='doctor_connections',
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    doctor_email = models.EmailField()
    doctor_name = models.CharField(max_length=120)
    specialty = models.CharField(max_length=120)
    clinic_name = models.CharField(max_length=160)
    clinic_address = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=4.8)
    review_count = models.PositiveIntegerField(default=0)
    experience_years = models.PositiveSmallIntegerField(default=0)
    next_available = models.CharField(max_length=120)
    source = models.CharField(max_length=40, default='demo_provider_directory')
    is_demo = models.BooleanField(default=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)
        db_table = 'visits_doctorconnection'

    def __str__(self):
        return f'{self.doctor_name} ({self.doctor_email})'


class DoctorConnectionRequest(models.Model):
    """A consent request emailed to a doctor or clinic."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='doctor_connection_requests',
    )
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    recipient_email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-requested_at',)
        db_table = 'visits_doctorconnectionrequest'

    def __str__(self):
        return f'Connection request to {self.recipient_email} ({self.status})'


class ConsultationSessionRequest(models.Model):
    """A paid request for a follow-up consultation with a connected doctor."""

    class Status(models.TextChoices):
        PAYMENT_PENDING = 'payment_pending', 'Payment pending'
        REQUESTED = 'requested', 'Requested'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        PROPOSED = 'proposed', 'New time proposed'
        PAYMENT_FAILED = 'payment_failed', 'Payment failed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consultation_session_requests',
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_consultation_sessions',
    )
    # DoctorConnection predates the app's migration history.  Keep its ID as
    # a stable audit reference while the request itself owns the patient and
    # doctor relations above.
    doctor_connection_id = models.PositiveIntegerField(null=True, blank=True)
    duration_minutes = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    preferred_datetime = models.DateTimeField()
    reason = models.CharField(max_length=240)
    notes = models.TextField(max_length=2000, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAYMENT_PENDING)
    # Keep these nullable until Razorpay has issued an identifier.  Empty strings
    # would clash with the unique constraint as soon as a second request is made.
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True, unique=True)
    proposed_datetime = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        db_table = 'visits_consultationsessionrequest'

    def __str__(self):
        return f'{self.patient} → {self.doctor} ({self.get_status_display()})'
