# Generated manually for the paid patient consultation request flow.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0010_marketplace_real_images'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsultationSessionRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('duration_minutes', models.PositiveSmallIntegerField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('preferred_datetime', models.DateTimeField()),
                ('reason', models.CharField(max_length=240)),
                ('notes', models.TextField(blank=True, max_length=2000)),
                ('status', models.CharField(choices=[('payment_pending', 'Payment pending'), ('requested', 'Requested'), ('payment_failed', 'Payment failed'), ('cancelled', 'Cancelled')], default='payment_pending', max_length=20)),
                ('razorpay_order_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('payment_verified_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor_connection_id', models.PositiveIntegerField(blank=True, null=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_consultation_sessions', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consultation_session_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',), 'db_table': 'visits_consultationsessionrequest'},
        ),
    ]
