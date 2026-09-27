from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0003_doctordirectorysearch')]

    operations = [
        migrations.CreateModel(
            name='DirectMessageThread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_message_threads', to='accounts.user')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='direct_message_threads', to='accounts.user')),
            ],
            options={'ordering': ('-updated_at',)},
        ),
        migrations.CreateModel(
            name='DirectMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(max_length=2000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_direct_messages', to='accounts.user')),
                ('thread', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='accounts.directmessagethread')),
            ],
            options={'ordering': ('created_at',)},
        ),
        migrations.AddConstraint(
            model_name='directmessagethread',
            constraint=models.UniqueConstraint(fields=('patient', 'doctor'), name='unique_patient_doctor_thread'),
        ),
    ]
