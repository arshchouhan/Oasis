from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_consultationsessionrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='EyeImageReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.FileField(upload_to='eye-image-reviews/%Y/%m/%d/')),
                ('original_name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='eye_image_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'symptoms_eyeimagereview',
                'ordering': ('-created_at',),
            },
        ),
    ]
