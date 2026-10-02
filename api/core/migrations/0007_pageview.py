from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_geminiusage'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_id', models.CharField(db_index=True, max_length=64)),
                ('path', models.CharField(max_length=255)),
                ('referrer_host', models.CharField(blank=True, default='', max_length=255)),
                ('device', models.CharField(blank=True, default='', max_length=16)),
                ('browser', models.CharField(blank=True, default='', max_length=24)),
                ('country', models.CharField(blank=True, default='', max_length=2)),
                ('is_new_visitor', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'readar_page_views',
            },
        ),
    ]
