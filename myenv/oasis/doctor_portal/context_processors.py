def calendar_status(request):
    """Expose the signed-in doctor's Calendar state to the shared portal shell."""
    connected = False
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and getattr(user, 'account_type', '') == 'doctor':
        from .models import GoogleCalendarConnection
        connected = GoogleCalendarConnection.objects.filter(user=user).exists()
    return {'doctor_calendar_connected': connected}
