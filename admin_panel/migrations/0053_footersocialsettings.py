from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0052_vesselshowcase_banner_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='FooterSocialSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('facebook_url', models.URLField(blank=True, max_length=255)),
                ('instagram_url', models.URLField(blank=True, max_length=255)),
                ('youtube_url', models.URLField(blank=True, max_length=255)),
                ('linkedin_url', models.URLField(blank=True, max_length=255)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Footer Social Settings',
                'verbose_name_plural': 'Footer Social Settings',
            },
        ),
    ]
