"""Patient authentication is under /pt/; signed-in tools live under /pt/dashboard/."""
from django.urls import path

from oasis import views as core_views
from . import auth_views, symptom_views, visit_views, task_views


urlpatterns = [
    path('dashboard/personal-workspace/', task_views.workspace, name='patient_personal_workspace'),
    path('', auth_views.patient_home, name='home'),
    path('login/', auth_views.patient_login, name='login'),
    path('register/', auth_views.patient_register, name='register'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('auth/google/', auth_views.google_login, name='google_login'),
    path('auth/google/callback/', auth_views.google_callback, name='google_callback'),
    path('dashboard/', core_views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/symptom-tracker/', symptom_views.symptom_tracker, name='symptom_tracker'),
    path('dashboard/symptom-tracker/save-eye-scan/', symptom_views.save_eye_scan, name='save_eye_scan'),
    path('dashboard/reports/', symptom_views.symptom_report, name='reports'),
    path('dashboard/visits/', visit_views.visits_home, name='visits'),
    path('dashboard/visits/find-doctor/', visit_views.visits_home, name='find_doctor'),
    path('dashboard/visits/search/', visit_views.doctor_search, name='doctor_search'),
    path('dashboard/visits/google-meet/', visit_views.patient_google_meet, name='patient_google_meet'),
    path('dashboard/visits/digital-reports/', visit_views.digital_reports, name='digital_reports'),
    path('dashboard/visits/doctor-directory/', visit_views.doctor_directory, name='doctor_directory'),
    path('dashboard/visits/direct-messages/start/', visit_views.direct_message_start, name='direct_message_start'),
    path('dashboard/visits/direct-messages/', visit_views.direct_messages, name='direct_messages'),
    path('dashboard/visits/direct-messages/<int:thread_id>/updates/', visit_views.direct_message_updates, name='direct_message_updates'),
    path('dashboard/visits/direct-messages/<int:thread_id>/', visit_views.direct_messages, name='direct_messages'),
    path('dashboard/visits/connection-request/<uuid:token>/', visit_views.doctor_connection_response, name='doctor_connection_response'),
    path('dashboard/visits/my-appointments/', visit_views.my_appointments, name='my_appointments'),
    path('dashboard/visits/my_appointments/', visit_views.my_appointments, name='my_appointments_legacy'),
    path('dashboard/screen-time/', core_views.home, name='screen_time'),
    path('dashboard/treatments/', core_views.home, name='treatments'),
    path('dashboard/environment/', core_views.guided_eye_care, name='environment'),
    path('dashboard/consult/', visit_views.visits_home, name='consult'),
    path('dashboard/learn/', core_views.home, name='learn'),
    path('dashboard/profile/', core_views.home, name='profile'),
]
