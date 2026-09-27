from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('doctor_portal', '0005_referralactivity')]

    operations = [
        migrations.AddField(model_name='referralthread', name='preferred_date', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='referralthread', name='priority', field=models.CharField(default='routine', max_length=16)),
        migrations.AddField(model_name='referralthread', name='referral_type', field=models.CharField(default='Specialist consultation', max_length=80)),
    ]
