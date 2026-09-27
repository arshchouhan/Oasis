from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('accounts', '0002_alter_user_managers_user_account_type')]

    operations = [
        migrations.CreateModel(
            name='DoctorDirectorySearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=120)),
                ('searched_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_directory_searches', to='accounts.user')),
            ],
            options={'ordering': ('-searched_at',)},
        ),
        migrations.AddConstraint(
            model_name='doctordirectorysearch',
            constraint=models.UniqueConstraint(fields=('user', 'query'), name='unique_patient_doctor_search'),
        ),
    ]
