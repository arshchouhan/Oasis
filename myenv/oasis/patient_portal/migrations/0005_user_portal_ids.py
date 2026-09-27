import uuid

from django.db import migrations, models


def assign_portal_ids(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all().iterator():
        if user.account_type == 'patient' and not user.patient_id:
            user.patient_id = f'PAT-{uuid.uuid4().hex[:10].upper()}'
            user.save(update_fields=('patient_id',))
        elif user.account_type == 'doctor' and not user.doctor_id:
            user.doctor_id = f'DR-{uuid.uuid4().hex[:10].upper()}'
            user.save(update_fields=('doctor_id',))


def remove_portal_ids(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.update(patient_id=None, doctor_id=None)


class Migration(migrations.Migration):
    dependencies = [('accounts', '0004_directmessagethread_directmessage')]

    operations = [
        migrations.AddField(
            model_name='user',
            name='doctor_id',
            field=models.CharField(blank=True, editable=False, max_length=16, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='patient_id',
            field=models.CharField(blank=True, editable=False, max_length=16, null=True, unique=True),
        ),
        migrations.RunPython(assign_portal_ids, remove_portal_ids),
    ]
