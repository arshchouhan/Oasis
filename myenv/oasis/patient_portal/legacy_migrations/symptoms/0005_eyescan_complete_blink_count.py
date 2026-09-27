from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('symptoms', '0004_eyescan_blink_detail_metrics')]

    operations = [
        migrations.AddField(model_name='eyescan', name='complete_blink_count', field=models.PositiveIntegerField(default=0)),
    ]
