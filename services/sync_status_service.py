"""
Course Sync Status
==================

Tracks each course's Canvas sync in the database, so the frontend can ask
whether a background sync has finished, and so two syncs of the same course
(Sync Now twice, or Sync Now landing on the scheduled sync) never run at once
and double-count scores.

One document per course, keyed by course id:
    status:       'running' | 'done' | 'failed'
    source:       'manual' | 'scheduled'
    started_at, updated_at, finished_at
    quizzes_done, quizzes_total
    error:        message shown to the instructor when status is 'failed'
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from config import Config
from mongodb import get_db

logger = logging.getLogger(__name__)

db = get_db()
sync_status_collection = db[Config.ACHIEVEUP_SYNC_STATUS_COLLECTION]

# A running sync refreshes updated_at every HEARTBEAT_EVERY, however long it
# spends waiting on Canvas (a New Quiz report can take minutes). One that
# hasn't for STALE_AFTER died partway (dyno restart, crash), so it no longer
# blocks a new sync and is reported as failed.
HEARTBEAT_EVERY = timedelta(minutes=1)
STALE_AFTER = timedelta(minutes=5)

# asyncio only keeps a weak reference to tasks, so a fire-and-forget task can
# be garbage collected before it finishes. Holding them here prevents that.
_background_tasks: set[asyncio.Task] = set()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_stale(doc: dict) -> bool:
    updated_at = doc.get('updated_at') or doc.get('started_at')
    return doc.get('status') == 'running' and (not updated_at or _now() - updated_at > STALE_AFTER)


def _to_response(course_id: str, doc: dict | None) -> dict:
    """The status as the frontend sees it. Dates are ISO strings in UTC."""
    if not doc:
        return {'course_id': str(course_id), 'status': 'idle'}

    status = doc.get('status')
    error = doc.get('error')
    if _is_stale(doc):
        status = 'failed'
        error = 'The sync was interrupted before it finished. Please try again.'

    def iso(value):
        return value.isoformat() + 'Z' if value else None

    return {
        'course_id': str(course_id),
        'status': status,
        'source': doc.get('source'),
        'started_at': iso(doc.get('started_at')),
        'updated_at': iso(doc.get('updated_at')),
        'finished_at': iso(doc.get('finished_at')),
        'quizzes_done': doc.get('quizzes_done', 0),
        'quizzes_total': doc.get('quizzes_total', 0),
        'error': error,
    }


async def get_sync_status(course_id: str) -> dict:
    doc = await sync_status_collection.find_one({'_id': str(course_id)})
    return _to_response(course_id, doc)


async def try_start_sync(course_id: str, source: str) -> dict | None:
    """Mark the course's sync as running. Returns the new status, or None if
    another sync of this course is already running.

    Atomic across requests and dynos: the filter only matches a course that
    isn't running (or whose run went stale). If the course is running, the
    upsert tries to insert a second document with the same _id and Mongo
    rejects it."""
    course_id = str(course_id)
    now = _now()
    try:
        doc = await sync_status_collection.find_one_and_update(
            {
                '_id': course_id,
                '$or': [
                    {'status': {'$ne': 'running'}},
                    {'updated_at': {'$lt': now - STALE_AFTER}},
                ],
            },
            {'$set': {
                'status': 'running',
                'source': source,
                'started_at': now,
                'updated_at': now,
                'finished_at': None,
                'quizzes_done': 0,
                'quizzes_total': 0,
                'error': None,
            }},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        return None
    return _to_response(course_id, doc)


async def update_sync_progress(course_id: str, quizzes_done: int, quizzes_total: int) -> None:
    """Record progress. Also refreshes updated_at, which keeps the run from
    being treated as stale. A failure here must not stop the sync."""
    try:
        await sync_status_collection.update_one(
            {'_id': str(course_id), 'status': 'running'},
            {'$set': {
                'quizzes_done': quizzes_done,
                'quizzes_total': quizzes_total,
                'updated_at': _now(),
            }},
        )
    except Exception as e:
        logger.error(f"Could not record sync progress for course {course_id}: {str(e)}")


async def _heartbeat(course_id: str) -> None:
    """Refresh updated_at until cancelled, so a long wait on Canvas isn't
    mistaken for a dead sync."""
    while True:
        await asyncio.sleep(HEARTBEAT_EVERY.total_seconds())
        try:
            await sync_status_collection.update_one(
                {'_id': str(course_id), 'status': 'running'},
                {'$set': {'updated_at': _now()}},
            )
        except Exception as e:
            logger.error(f"Could not record sync heartbeat for course {course_id}: {str(e)}")


async def finish_sync(course_id: str, error: str | None = None) -> None:
    now = _now()
    try:
        await sync_status_collection.update_one(
            {'_id': str(course_id)},
            {'$set': {
                'status': 'failed' if error else 'done',
                'error': error,
                'finished_at': now,
                'updated_at': now,
            }},
        )
    except Exception as e:
        logger.error(f"Could not record sync result for course {course_id}: {str(e)}")


async def run_tracked_sync(canvas_token: str, course_id: str, course_name: str = None,
                           prepare=None) -> dict:
    """Run the course sync and record its progress and outcome. The caller
    must have claimed the course with try_start_sync first.

    prepare: optional async callable run before the sync (the scheduled sync
    refreshes quiz questions first). It runs under the same heartbeat, so a
    slow one isn't mistaken for a dead sync, and its failure fails the sync."""
    from services.canvas_submissions_service import sync_course_submissions_direct

    async def on_progress(done: int, total: int):
        await update_sync_progress(course_id, done, total)

    heartbeat = asyncio.create_task(_heartbeat(course_id))
    try:
        if prepare:
            await prepare()
        result = await sync_course_submissions_direct(
            canvas_token, course_id, course_name, on_progress=on_progress)
    except Exception as e:
        logger.error(f"Sync of course {course_id} failed: {str(e)}", exc_info=True)
        await finish_sync(course_id, 'The sync failed unexpectedly. Please try again.')
        return {'error': 'Internal server error', 'statusCode': 500}
    finally:
        heartbeat.cancel()

    if isinstance(result, dict) and 'error' in result:
        await finish_sync(course_id, result.get('message') or 'The sync could not be completed. Please try again.')
    else:
        await finish_sync(course_id)
    return result


def start_background_sync(canvas_token: str, course_id: str, course_name: str = None) -> asyncio.Task:
    """Run run_tracked_sync in the background, keeping a reference to the task
    until it finishes."""
    task = asyncio.create_task(run_tracked_sync(canvas_token, course_id, course_name))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
