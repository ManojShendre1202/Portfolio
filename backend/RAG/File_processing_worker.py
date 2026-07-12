import logging
import time

from workflow.engine.tasks.base_task import Task, TaskResult
from backend.RAG.File_processing.File_classification import classify_and_extract
from backend.RAG.File_processing.File_graph import build_graph
from api.core.service.ReadarJobService import ReadarJobService

logger = logging.getLogger(__name__)


def run(task: Task, update_queue):
    comments = []
    start    = time.time()

    def log(msg: str) -> None:
        logger.info(msg)
        comments.append(msg)
        try:
            update_queue.put((task.revision_id, task.stage_name, msg))
        except Exception:
            pass

    extracted_path    = ''
    graph_path        = ''
    entity_graph_path = ''

    try:
        section_data = task.payload.get('section_data', {})
        rel_path     = section_data.get('file_path', '')
        file_type    = section_data.get('file_type', '')
        job_id       = task.revision_id

        log(f"File: {rel_path.split('/')[-1]}")

        # Step 1 — extract text
        extracted_path = classify_and_extract(rel_path, file_type, job_id, log)

        if not extracted_path:
            raise ValueError("Text extraction returned nothing — likely a scanned PDF")

        ReadarJobService.set_extracted_text(job_id, extracted_path)

        # Step 2 — build hierarchical graph + entity graph + embeddings
        log("Starting graph build")
        graph_path, entity_graph_path, suggested_actions = build_graph(extracted_path, job_id, log)

        # Store graph paths in section_data structured_data field
        ReadarJobService.set_structured_data(job_id, {
            'graph_path': graph_path,
            'entity_graph_path': entity_graph_path,
        })
        ReadarJobService.set_action_suggestions(job_id, suggested_actions)

        log("Processing complete")

    except Exception as e:
        log(f"Error: {e}")
        return TaskResult(
            status='failed',
            comments=comments,
            file_paths=[],
            time_taken=round(time.time() - start, 2),
            error=str(e),
        )

    return TaskResult(
        status='completed',
        comments=comments,
        file_paths=[p for p in [extracted_path, graph_path, entity_graph_path] if p],
        time_taken=round(time.time() - start, 2),
        error=None,
    )
