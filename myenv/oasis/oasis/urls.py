"""
URL configuration for oasis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from oasis import views as core_views
from patient_portal import auth_views

urlpatterns = [
    # Public site entry points. The home page is intentionally independent of
    # either portal so it can grow into the public ClearEye landing page.
    path('', core_views.site_home, name='site_home'),
    path('login/', auth_views.login_view, name='site_login'),
    path('register/', auth_views.register, name='site_register'),
    path('logout/', auth_views.logout_view, name='site_logout'),
    path('auth/google/', auth_views.google_login, name='site_google_login'),
    path('auth/google/callback/', auth_views.google_callback, name='site_google_callback'),
    path('pt/', include('patient_portal.urls')),
    path('dr/', include('doctor_portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
