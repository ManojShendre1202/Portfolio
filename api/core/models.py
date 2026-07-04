from django.db import models


class ReadarJob(models.Model):
    file_name    = models.CharField(max_length=255)
    file_size    = models.BigIntegerField(default=0)
    client_id    = models.CharField(max_length=64, db_index=True, default='')
    status       = models.CharField(max_length=30, default='queued')
    section_data = models.JSONField(default=dict)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'readar_jobs'
