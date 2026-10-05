from django import template
from patient_portal.models import User

register = template.Library()


@register.simple_tag
def avatar_url(person):
    if isinstance(person, User):
        return person.profile_image_url
    if isinstance(person, str) and person:
        return User.objects.filter(email__iexact=person).values_list('profile_image_url', flat=True).first() or ''
    return ''
