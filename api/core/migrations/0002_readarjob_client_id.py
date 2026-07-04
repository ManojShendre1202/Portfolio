from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='readarjob',
            name='client_id',
            field=models.CharField(db_index=True, default='', max_length=64),
        ),
    ]
