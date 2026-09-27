from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('symptoms', '0003_eyescan_sampled_frames')]

    operations = [
        migrations.AddField(model_name='eyescan', name='incomplete_blink_rate', field=models.FloatField(default=0)),
        migrations.AddField(model_name='eyescan', name='average_interblink_interval', field=models.FloatField(default=0)),
        migrations.AddField(model_name='eyescan', name='average_blink_duration', field=models.FloatField(default=0)),
        migrations.AddField(model_name='eyescan', name='average_eye_opening', field=models.FloatField(default=0)),
    ]
