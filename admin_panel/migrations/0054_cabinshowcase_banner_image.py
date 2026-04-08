from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0053_footersocialsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='cabinshowcase',
            name='banner_image',
            field=models.ImageField(blank=True, help_text='Banner image (4:1 ratio)', null=True, upload_to='cabin_showcase/banners/'),
        ),
    ]
