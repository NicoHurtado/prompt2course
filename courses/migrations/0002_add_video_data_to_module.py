# Generated manually for video_data field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='module',
            name='video_data',
            field=models.JSONField(blank=True, default=dict),
        ),
    ] 