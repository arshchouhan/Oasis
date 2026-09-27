from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('doctor_portal', '0002_googlecalendarconnection'),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedDigitalReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_scan_id', models.PositiveBigIntegerField()),
                ('generated_at', models.DateTimeField()),
                ('blink_rate', models.FloatField(default=0)),
                ('redness_score', models.FloatField(default=0)),
                ('tracking_quality', models.PositiveIntegerField(default=0)),
                ('shared_at', models.DateTimeField(auto_now_add=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_reports', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-shared_at',)},
        ),
        migrations.AddConstraint(
            model_name='shareddigitalreport',
            constraint=models.UniqueConstraint(fields=('patient', 'doctor', 'source_scan_id'), name='unique_shared_digital_report'),
        ),
    ]
