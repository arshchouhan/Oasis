from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('doctor_portal', '0004_referralthread')]

    operations = [
        migrations.CreateModel(
            name='ReferralActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=40)),
                ('detail', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referral_activities', to=settings.AUTH_USER_MODEL)),
                ('referral', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to='doctor_portal.referralthread')),
            ],
            options={'ordering': ('created_at',)},
        ),
    ]
