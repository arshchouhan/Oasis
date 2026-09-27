from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('doctor_portal', '0003_shareddigitalreport')]

    operations = [
        migrations.CreateModel(
            name='ReferralThread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField(blank=True, max_length=2000)),
                ('status', models.CharField(choices=[('open', 'Open'), ('accepted', 'Accepted'), ('closed', 'Closed')], default='open', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referral_threads', to=settings.AUTH_USER_MODEL)),
                ('referred_doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_referrals', to=settings.AUTH_USER_MODEL)),
                ('referring_doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_referrals', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-updated_at',)},
        ),
    ]
