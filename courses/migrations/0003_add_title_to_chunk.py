# Generated manually for title field in Chunk

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_add_video_data_to_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='chunk',
            name='title',
            field=models.CharField(blank=True, max_length=300),
        ),
    ] 