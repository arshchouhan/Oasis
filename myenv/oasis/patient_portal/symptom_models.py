from django.conf import settings
from django.db import models


class EyeScan(models.Model):
    """The user's current one-minute eye assessment and its derived metrics."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='eye_scans')
    left_image_url = models.URLField(max_length=500)
    right_image_url = models.URLField(max_length=500)
    left_public_id = models.CharField(max_length=255, blank=True)
    right_public_id = models.CharField(max_length=255, blank=True)
    recording_url = models.URLField(max_length=500, blank=True)
    recording_public_id = models.CharField(max_length=255, blank=True)
    duration_seconds = models.PositiveIntegerField(default=60)
    blink_count = models.PositiveIntegerField(default=0)
    blink_rate = models.FloatField(default=0)
    incomplete_blink_rate = models.FloatField(default=0)
    complete_blink_count = models.PositiveIntegerField(default=0)
    average_interblink_interval = models.FloatField(default=0)
    average_blink_duration = models.FloatField(default=0)
    average_eye_opening = models.FloatField(default=0)
    left_ear = models.FloatField(default=0)
    right_ear = models.FloatField(default=0)
    redness_index = models.FloatField(default=0)
    tracking_quality = models.PositiveIntegerField(default=0)
    redness_score = models.FloatField(default=0)
    sampled_frames = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        db_table = 'symptoms_eyescan'

    def __str__(self):
        return f'Eye scan for {self.user} at {self.created_at:%Y-%m-%d %H:%M}'
