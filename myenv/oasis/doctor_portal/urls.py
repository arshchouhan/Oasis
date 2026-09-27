from django.urls import path
from patient_portal import auth_views

from . import views

urlpatterns = [
    path('', views.home, name='doctor_home'),
    path('login/', auth_views.doctor_login, name='doctor_login'),
    path('register/', auth_views.doctor_register, name='doctor_register'),
    path('dashboard/', views.dashboard, name='doctor_dashboard'),
    path('dashboard/upcoming-meetings/', views.upcoming_meetings, name='doctor_upcoming_meetings'),
    path('dashboard/referrals/', views.referral_manager, name='doctor_referral_manager'),
    path('dashboard/connections/', views.connections, name='doctor_connections'),
    path('dashboard/connections/direct-messages/', views.direct_messages, name='doctor_direct_messages'),
    path('dashboard/connections/direct-messages/<int:thread_id>/', views.direct_messages, name='doctor_direct_messages'),
    path('dashboard/connections/direct-messages/<int:thread_id>/decision/', views.connection_request_decision, name='doctor_connection_request_decision'),
    path('dashboard/community/', views.community, name='doctor_community'),
    path('dashboard/profile/', views.profile, name='doctor_profile'),
    path('dashboard/google-calendar/connect/', views.google_calendar_connect, name='doctor_google_calendar_connect'),
    path('dashboard/google-calendar/callback/', views.google_calendar_callback, name='doctor_google_calendar_callback'),
    path('dashboard/google-calendar/disconnect/', views.google_calendar_disconnect, name='doctor_google_calendar_disconnect'),
    path('dashboard/google-calendar/meet/', views.google_meet_details, name='doctor_google_meet'),
    path('dashboard/patients/<int:patient_id>/schedule-meet/', views.schedule_google_meet, name='doctor_schedule_meet'),
    path('dashboard/patients/<int:patient_id>/meet-workspace/', views.meet_workspace, name='doctor_meet_workspace'),
    path('dashboard/patients/<int:patient_id>/digital-reports/', views.patient_digital_reports, name='doctor_patient_digital_reports'),
    path('dashboard/patients/<int:patient_id>/reports-workspace/', views.reports_workspace, name='doctor_reports_workspace'),
    path('dashboard/patients/<int:patient_id>/referrals/', views.patient_referrals, name='doctor_patient_referrals'),
    path('dashboard/patients/<int:patient_id>/referral-workspace/', views.referral_workspace, name='doctor_referral_workspace'),
]
