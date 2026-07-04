import os
import socket

from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from api.core.service.ReadarJobService import ReadarJobService


@csrf_exempt
def uploadDocument(request):
    files      = request.FILES['file']
    client_id  = request.POST.get('client_id', '')
    path       = default_storage.save(f'uploads/{files.name}', files)
    job        = ReadarJobService.create_job(files.name, files.size, path, files.content_type, client_id)

    signal_host = os.environ.get('SIGNAL_HOST', '127.0.0.1')
    signal_port = int(os.environ.get('SIGNAL_PORT', 9000))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((signal_host, signal_port))
    sock.sendall(f"{job.id}:File_processing".encode())
    sock.recv(16)
    sock.close()

    return JsonResponse({'status': 'success', 'job_id': job.id})


@require_GET
def getJob(request, job_id):
    try:
        job = ReadarJobService.get_job(job_id)
    except Exception:
        return JsonResponse({'error': 'not found'}, status=404)

    return JsonResponse({
        'id':           job.id,
        'file_name':    job.file_name,
        'file_size':    job.file_size,
        'status':       job.status,
        'section_data': job.section_data,
    })


@require_GET
def getJobsByClient(request):
    client_id = request.GET.get('client_id', '').strip()
    if not client_id:
        return JsonResponse({'error': 'client_id required'}, status=400)

    jobs = ReadarJobService.get_by_client(client_id)

    # section_data contains DateTimeField in created_at — convert to str
    result = []
    for j in jobs:
        result.append({
            'id':           j['id'],
            'file_name':    j['file_name'],
            'file_size':    j['file_size'],
            'status':       j['status'],
            'section_data': j['section_data'],
            'created_at':   j['created_at'].isoformat(),
        })

    return JsonResponse({'jobs': result})
