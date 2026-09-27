from django.contrib import admin
from .models import DoctorConnection, DoctorConnectionRequest


@admin.register(DoctorConnection)
class DoctorConnectionAdmin(admin.ModelAdmin):
    list_display = ('doctor_name', 'doctor_email', 'clinic_name', 'is_demo', 'updated_at')
    list_filter = ('is_demo', 'source')
    search_fields = ('doctor_name', 'doctor_email', 'clinic_name')


@admin.register(DoctorConnectionRequest)
class DoctorConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('recipient_email', 'status', 'requested_at', 'responded_at')
    list_filter = ('status',)
    search_fields = ('recipient_email',)
