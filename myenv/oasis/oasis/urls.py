"""
URL configuration for oasis project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app1 import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('dashboard/', views.home, name='dashboard'),
    path('symptom-tracker/', views.home, name='symptom_tracker'),
    path('screen-time/', views.home, name='screen_time'),
    path('treatments/', views.home, name='treatments'),
    path('environment/', views.home, name='environment'),
    path('reports/', views.home, name='reports'),
    path('consult/', views.home, name='consult'),
    path('learn/', views.home, name='learn'),
    path('profile/', views.home, name='profile'),
]
