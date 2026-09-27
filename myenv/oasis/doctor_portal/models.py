from django.conf import settings
from django.db import models


class DoctorProfile(models.Model):
    """Professional details shown within the Doctor Portal."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=120, blank=True)
    registration_number = models.CharField(max_length=80, blank=True)
    clinic_name = models.CharField(max_length=160, blank=True)
    city = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    biography = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Doctor profile: {self.user}'


class GoogleCalendarConnection(models.Model):
    """OAuth tokens a doctor grants specifically for their Calendar events."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_calendar_connection')
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)


class SharedDigitalReport(models.Model):
    """A patient-authorised snapshot of a generated eye assessment for one doctor."""

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_reports')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reports')
    source_scan_id = models.PositiveBigIntegerField()
    generated_at = models.DateTimeField()
    blink_rate = models.FloatField(default=0)
    redness_score = models.FloatField(default=0)
    tracking_quality = models.PositiveIntegerField(default=0)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-shared_at',)
        constraints = [models.UniqueConstraint(fields=('patient', 'doctor', 'source_scan_id'), name='unique_shared_digital_report')]


class ReferralThread(models.Model):
    """A doctor-to-doctor referral conversation for an accepted patient."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        ACCEPTED = 'accepted', 'Accepted'
        CLOSED = 'closed', 'Closed'

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_threads')
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_referrals')
    referred_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_referrals')
    note = models.TextField(max_length=2000, blank=True)
    referral_type = models.CharField(max_length=80, default='Specialist consultation')
    priority = models.CharField(max_length=16, default='routine')
    preferred_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)


class ReferralActivity(models.Model):
    """An immutable milestone in a doctor-to-doctor referral thread."""

    referral = models.ForeignKey(ReferralThread, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_activities')
    action = models.CharField(max_length=40)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)
