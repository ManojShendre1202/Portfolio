from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_pageview'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageview',
            name='os',
            field=models.CharField(blank=True, default='', max_length=12),
        ),
        migrations.AddField(
            model_name='pageview',
            name='ua_hash',
            field=models.CharField(blank=True, db_index=True, default='', max_length=12),
        ),
        migrations.AddField(
            model_name='pageview',
            name='bot_reason',
            field=models.CharField(blank=True, default='', max_length=24),
        ),
        # Rows that already exist were recorded before any classification, so
        # they are labelled 'legacy' instead of being guessed at. New rows get
        # the model default ('unverified') via the AlterField below.
        migrations.AddField(
            model_name='pageview',
            name='visit_class',
            field=models.CharField(db_index=True, default='legacy', max_length=10),
        ),
        migrations.AlterField(
            model_name='pageview',
            name='visit_class',
            field=models.CharField(db_index=True, default='unverified', max_length=10),
        ),
    ]
