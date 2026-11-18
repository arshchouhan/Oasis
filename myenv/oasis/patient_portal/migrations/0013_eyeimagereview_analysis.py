from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('accounts', '0012_eye_image_review')]
    operations = [migrations.AddField(model_name='eyeimagereview', name='analysis', field=models.JSONField(default=dict, blank=True))]
