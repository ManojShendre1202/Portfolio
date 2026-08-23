"""
doc_pages.py — hands the split-view left pane the raw curated-doc HTML
(already captured + id-stamped by Readar_dev/html_parser/html_parser.py into
data/html/raw/{doc}/{chapter}_ids.html) plus the location metadata it needs
to render it: base_href (per-chapter for docker/opencv/chroma, whose chapters
sit at different relative depths on their site — see chapter_base_href below
— one value for every other doc, since their chapters are flat siblings).

All HTML patching (injecting <base href>, dropping the source site's
prefers-color-scheme dark-mode guard, the citation-highlight-by-dom_id
listener, the same-tutorial chapter-link interceptor, and CSS fallbacks for
docs whose own styling doesn't survive being framed standalone) is done
client-side in frontend/src/pages/readar/docPageRender.js — this view is
just a file server with a routing table, no rendering logic.
"""

import logging
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

DATA_ROOT = Path(settings.BASE_DIR) / 'documents' / 'raw'

DOC_PAGE_SOURCES = {
    'python-tutorial': {
        'dir':       'python_tutorial',
        'base_href': 'https://docs.python.org/3/tutorial/',
        'chapters': [
            'appetite', 'interpreter', 'introduction', 'controlflow',
            'datastructures', 'modules', 'inputoutput', 'errors', 'classes',
            'stdlib', 'stdlib2', 'venv', 'whatnow', 'interactive',
            'floatingpoint', 'appendix',
        ],
    },
    'pytorch': {
        'dir':       'pytorch',
        'base_href': 'https://docs.pytorch.org/tutorials/beginner/basics/',
        'chapters': [
            'intro', 'quickstart_tutorial', 'tensorqs_tutorial', 'data_tutorial',
            'transforms_tutorial', 'buildmodel_tutorial', 'autogradqs_tutorial',
            'optimization_tutorial', 'saveloadrun_tutorial',
        ],
    },
    'numpy': {
        'dir':       'numpy',
        'base_href': 'https://numpy.org/doc/stable/user/',
        'chapters': [
            'absolute_beginners', 'quickstart', 'basics.types', 'basics.creation',
            'basics.indexing', 'basics.broadcasting', 'basics.copies',
            'basics.rec', 'numpy-for-matlab-users',
        ],
    },
    'langchain': {
        'dir':       'langchain',
        'base_href': 'https://docs.langchain.com/oss/python/langchain/',
        'chapters': [
            'overview', 'install', 'quickstart', 'models', 'messages',
            'tools', 'agents', 'short-term-memory', 'retrieval', 'structured-output',
        ],
    },
    'langgraph': {
        'dir':       'langgraph',
        'base_href': 'https://docs.langchain.com/oss/python/langgraph/',
        'chapters': [
            'overview', 'quickstart', 'graph-api', 'use-graph-api',
            'application-structure', 'persistence', 'add-memory',
            'streaming', 'interrupts',
        ],
    },
    'postgresql': {
        'dir':       'postgresql',
        'base_href': 'https://www.postgresql.org/docs/current/',
        'chapters': [
            'tutorial-start', 'tutorial-install', 'tutorial-arch', 'tutorial-createdb',
            'tutorial-accessdb', 'tutorial-sql', 'tutorial-sql-intro', 'tutorial-concepts',
            'tutorial-table', 'tutorial-populate', 'tutorial-select', 'tutorial-join',
            'tutorial-agg', 'tutorial-update', 'tutorial-delete', 'tutorial-advanced',
            'tutorial-advanced-intro', 'tutorial-views', 'tutorial-fk',
            'tutorial-transactions', 'tutorial-window', 'tutorial-inheritance',
            'tutorial-conclusion',
        ],
    },
    'git': {
        'dir':       'git',
        # all book pages sit flat under this one path, despite the "book/en/v2/"
        # naming — no per-chapter subdirectories, unlike docker/opencv/chroma below.
        'base_href': 'https://git-scm.com/book/en/v2/',
        'chapters': [
            'what_is_git', 'first_time_setup', 'getting_a_repository',
            'recording_changes', 'viewing_commit_history', 'undoing_things',
            'working_with_remotes', 'branches_in_a_nutshell',
            'basic_branching_and_merging', 'rebasing',
        ],
    },
    # docker/opencv/chroma pages live at different relative depths under their
    # site (see Readar_dev/html_parser/fetch_doc.py's DOC_CONFIGS "pages" form),
    # so a single doc-level base_href can't resolve every chapter's relative
    # asset/link paths — each chapter gets its own base_href (the page's real URL).
    'docker': {
        'dir': 'docker',
        'chapter_base_href': {
            'what_is_a_container':            'https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/',
            'what_is_an_image':                'https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/',
            'what_is_a_registry':              'https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-registry/',
            'what_is_docker_compose':          'https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-docker-compose/',
            'understanding_image_layers':      'https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/',
            'writing_a_dockerfile':            'https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/',
            'build_tag_and_publish_an_image':  'https://docs.docker.com/get-started/docker-concepts/building-images/build-tag-and-publish-an-image/',
            'using_the_build_cache':           'https://docs.docker.com/get-started/docker-concepts/building-images/using-the-build-cache/',
            'multi_stage_builds':              'https://docs.docker.com/get-started/docker-concepts/building-images/multi-stage-builds/',
            'publishing_ports':                'https://docs.docker.com/get-started/docker-concepts/running-containers/publishing-ports/',
            'persisting_container_data':       'https://docs.docker.com/get-started/docker-concepts/running-containers/persisting-container-data/',
        },
        'chapters': [
            'what_is_a_container', 'what_is_an_image', 'what_is_a_registry',
            'what_is_docker_compose', 'understanding_image_layers',
            'writing_a_dockerfile', 'build_tag_and_publish_an_image',
            'using_the_build_cache', 'multi_stage_builds', 'publishing_ports',
            'persisting_container_data',
        ],
    },
    'opencv': {
        'dir': 'opencv',
        'chapter_base_href': {
            'display_image':             'https://docs.opencv.org/4.x/db/deb/tutorial_display_image.html',
            'video_display':             'https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html',
            'drawing_functions':         'https://docs.opencv.org/4.x/dc/da5/tutorial_py_drawing_functions.html',
            'basic_ops':                 'https://docs.opencv.org/4.x/d3/df2/tutorial_py_basic_ops.html',
            'image_arithmetics':         'https://docs.opencv.org/4.x/d0/d86/tutorial_py_image_arithmetics.html',
            'colorspaces':               'https://docs.opencv.org/4.x/df/d9d/tutorial_py_colorspaces.html',
            'geometric_transformations': 'https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html',
            'thresholding':              'https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html',
            'filtering':                 'https://docs.opencv.org/4.x/d4/d13/tutorial_py_filtering.html',
            'canny':                     'https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html',
        },
        'chapters': [
            'display_image', 'video_display', 'drawing_functions', 'basic_ops',
            'image_arithmetics', 'colorspaces', 'geometric_transformations',
            'thresholding', 'filtering', 'canny',
        ],
    },
    'chroma': {
        'dir': 'chroma',
        'chapter_base_href': {
            'introduction':        'https://docs.trychroma.com/docs/overview/introduction',
            'getting_started':     'https://docs.trychroma.com/docs/overview/getting-started',
            'manage_collections':  'https://docs.trychroma.com/docs/collections/manage-collections',
            'add_data':            'https://docs.trychroma.com/docs/collections/add-data',
            'update_data':         'https://docs.trychroma.com/docs/collections/update-data',
            'delete_data':         'https://docs.trychroma.com/docs/collections/delete-data',
            'query_and_get':       'https://docs.trychroma.com/docs/querying-collections/query-and-get',
            'metadata_filtering':  'https://docs.trychroma.com/docs/querying-collections/metadata-filtering',
            'embedding_functions': 'https://docs.trychroma.com/docs/embeddings/embedding-functions',
            'clients':             'https://docs.trychroma.com/docs/run-chroma/clients',
        },
        'chapters': [
            'introduction', 'getting_started', 'manage_collections', 'add_data',
            'update_data', 'delete_data', 'query_and_get', 'metadata_filtering',
            'embedding_functions', 'clients',
        ],
    },
}

@require_GET
@xframe_options_exempt
def getDocPage(request, doc_id, chapter):
    source = DOC_PAGE_SOURCES.get(doc_id)
    if not source or chapter not in source['chapters']:
        logger.warning('getDocPage: unknown doc_id=%s chapter=%s', doc_id, chapter)
        return HttpResponse('Not found', status=404)

    file_path = DATA_ROOT / source['dir'] / f'{chapter}_ids.html'
    if not file_path.exists():
        logger.error('getDocPage: expected file missing on disk: %s', file_path)
        return HttpResponse('Not found', status=404)

    base_href = source.get('chapter_base_href', {}).get(chapter, source.get('base_href'))
    raw_html  = file_path.read_text(encoding='utf-8')
    logger.info('getDocPage served: doc_id=%s chapter=%s', doc_id, chapter)
    return JsonResponse({'html': raw_html, 'base_href': base_href})
