from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('symptoms', '0005_eyescan_complete_blink_count')]

    operations = [
        migrations.AddField(model_name='eyescan', name='left_ear', field=models.FloatField(default=0)),
        migrations.AddField(model_name='eyescan', name='right_ear', field=models.FloatField(default=0)),
        migrations.AddField(model_name='eyescan', name='redness_index', field=models.FloatField(default=0)),
    ]
