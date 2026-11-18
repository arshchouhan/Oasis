from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0007_user_profile_image_url_doctorconnection_and_more')]

    operations = [
        migrations.CreateModel(
            name='ColourVisionSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_plate', models.PositiveSmallIntegerField(default=0)),
                ('correct_answers', models.PositiveSmallIntegerField(default=0)),
                ('elapsed_seconds', models.PositiveIntegerField(default=0)),
                ('responses', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('ended', 'Ended early')], default='active', max_length=12)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='colour_vision_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-updated_at',)},
        ),
    ]
