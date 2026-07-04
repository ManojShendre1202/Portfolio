from api.core.models import ReadarJob


STAGES = ['FILE_CLASSIFY', 'EXTRACT', 'STRUCTURE', 'INDEX', 'ACTION_SUGGEST']


def _initial_section_data(file_path, file_type):
    return {
        'file_path':          file_path,
        'file_type':          file_type,
        'document_type':      None,
        'extraction_method':  None,
        'extracted_text':     None,
        'structured_data':    None,
        'action_suggestions': [],
        'stages': {
            stage: {'status': 'pending', 'comments': [], 'time_taken': 0}
            for stage in STAGES
        },
    }


class ReadarJobService:

    @staticmethod
    def create_job(file_name, file_size, file_path, file_type, client_id=''):
        job = ReadarJob.objects.create(
            file_name    = file_name,
            file_size    = file_size,
            client_id    = client_id,
            status       = 'queued',
            section_data = _initial_section_data(file_path, file_type),
        )
        return job

    @staticmethod
    def get_job(job_id):
        return ReadarJob.objects.get(id=job_id)

    @staticmethod
    def get_by_client(client_id):
        return list(
            ReadarJob.objects.filter(client_id=client_id)
            .order_by('-created_at')
            .values('id', 'file_name', 'file_size', 'status', 'section_data', 'created_at')
        )

    @staticmethod
    def update_stage_status(job_id, stage_name, status, comments=None, time_taken=None):
        job = ReadarJob.objects.get(id=job_id)
        stage = job.section_data['stages'][stage_name]
        stage['status'] = status
        if comments is not None:
            stage['comments'] = comments
        if time_taken is not None:
            stage['time_taken'] = time_taken
        job.save(update_fields=['section_data'])

    @staticmethod
    def set_document_type(job_id, document_type, extraction_method):
        job = ReadarJob.objects.get(id=job_id)
        job.section_data['document_type']     = document_type
        job.section_data['extraction_method'] = extraction_method
        job.save(update_fields=['section_data'])

    @staticmethod
    def set_extracted_text(job_id, extracted_text):
        job = ReadarJob.objects.get(id=job_id)
        job.section_data['extracted_text'] = extracted_text
        job.save(update_fields=['section_data'])

    @staticmethod
    def set_structured_data(job_id, structured_data):
        job = ReadarJob.objects.get(id=job_id)
        job.section_data['structured_data'] = structured_data
        job.save(update_fields=['section_data'])

    @staticmethod
    def set_action_suggestions(job_id, suggestions):
        job = ReadarJob.objects.get(id=job_id)
        job.section_data['action_suggestions'] = suggestions
        job.save(update_fields=['section_data'])

    @staticmethod
    def complete_job(job_id):
        ReadarJob.objects.filter(id=job_id).update(status='completed')

    @staticmethod
    def fail_job(job_id):
        ReadarJob.objects.filter(id=job_id).update(status='failed')

    @staticmethod
    def set_processing(job_id):
        ReadarJob.objects.filter(id=job_id).update(status='processing')
