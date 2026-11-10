import asyncio
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from pymongo.errors import DuplicateKeyError

from services import sync_status_service as service


def running_doc(age=timedelta(0)):
    started = service._now() - age
    return {'_id': '100', 'status': 'running', 'source': 'manual', 'started_at': started,
            'updated_at': started, 'finished_at': None, 'quizzes_done': 3, 'quizzes_total': 8,
            'error': None}


class SyncStatusTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.collection = MagicMock()
        self.collection.update_one = AsyncMock()
        patcher = patch.object(service, 'sync_status_collection', self.collection)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_course_never_synced_is_idle(self):
        self.collection.find_one = AsyncMock(return_value=None)
        self.assertEqual(await service.get_sync_status('100'), {'course_id': '100', 'status': 'idle'})

    async def test_running_sync_reports_progress(self):
        self.collection.find_one = AsyncMock(return_value=running_doc())
        status = await service.get_sync_status('100')
        self.assertEqual((status['status'], status['quizzes_done'], status['quizzes_total']),
                         ('running', 3, 8))
        self.assertTrue(status['started_at'].endswith('Z'))

    async def test_run_that_stopped_updating_reports_failed(self):
        self.collection.find_one = AsyncMock(return_value=running_doc(service.STALE_AFTER + timedelta(seconds=1)))
        status = await service.get_sync_status('100')
        self.assertEqual(status['status'], 'failed')
        self.assertIn('interrupted', status['error'])

    async def test_claim_returns_running_status(self):
        self.collection.find_one_and_update = AsyncMock(return_value=running_doc())
        status = await service.try_start_sync('100', 'manual')
        self.assertEqual(status['status'], 'running')

    async def test_claim_refused_while_running(self):
        # The filter doesn't match a running course, so the upsert collides on _id.
        self.collection.find_one_and_update = AsyncMock(side_effect=DuplicateKeyError('dup'))
        self.assertIsNone(await service.try_start_sync('100', 'manual'))

    async def test_tracked_sync_records_progress_then_done(self):
        async def fake_sync(token, course_id, course_name, on_progress):
            await on_progress(1, 2)
            return {'message': 'Sync completed (Direct)'}

        with patch('services.canvas_submissions_service.sync_course_submissions_direct', fake_sync):
            await service.run_tracked_sync('canvas-token', '100')

        progress, finish = self.collection.update_one.await_args_list
        self.assertEqual(progress.args[1]['$set']['quizzes_done'], 1)
        self.assertEqual(finish.args[1]['$set']['status'], 'done')

    async def test_tracked_sync_records_error_result_as_failed(self):
        sync = AsyncMock(return_value={'error': 'Canvas error', 'message': 'Canvas is down', 'statusCode': 502})
        with patch('services.canvas_submissions_service.sync_course_submissions_direct', sync):
            await service.run_tracked_sync('canvas-token', '100')
        update = self.collection.update_one.await_args.args[1]['$set']
        self.assertEqual((update['status'], update['error']), ('failed', 'Canvas is down'))

    async def test_tracked_sync_records_exception_as_failed(self):
        sync = AsyncMock(side_effect=RuntimeError('boom'))
        with patch('services.canvas_submissions_service.sync_course_submissions_direct', sync):
            result = await service.run_tracked_sync('canvas-token', '100')
        self.assertEqual(result['statusCode'], 500)
        self.assertEqual(self.collection.update_one.await_args.args[1]['$set']['status'], 'failed')

    async def test_heartbeat_keeps_a_long_wait_alive_and_stops_after(self):
        release = asyncio.Event()

        async def slow_sync(*args, **kwargs):
            await release.wait()  # e.g. waiting on a New Quiz report
            return {}

        with patch.object(service, 'HEARTBEAT_EVERY', timedelta(milliseconds=10)), \
             patch('services.canvas_submissions_service.sync_course_submissions_direct', slow_sync):
            task = asyncio.create_task(service.run_tracked_sync('canvas-token', '100'))
            await asyncio.sleep(0.05)
            beats = [c for c in self.collection.update_one.await_args_list
                     if set(c.args[1]['$set']) == {'updated_at'}]
            self.assertGreaterEqual(len(beats), 2)

            release.set()
            await task
            calls_after_finish = self.collection.update_one.await_count
            await asyncio.sleep(0.05)
            self.assertEqual(self.collection.update_one.await_count, calls_after_finish)

    async def test_slow_preparation_is_covered_by_the_heartbeat(self):
        release = asyncio.Event()
        sync = AsyncMock(return_value={})

        async def slow_prepare():
            await release.wait()  # e.g. the scheduled sync refreshing quiz questions

        with patch.object(service, 'HEARTBEAT_EVERY', timedelta(milliseconds=10)), \
             patch('services.canvas_submissions_service.sync_course_submissions_direct', sync):
            task = asyncio.create_task(service.run_tracked_sync('canvas-token', '100', prepare=slow_prepare))
            await asyncio.sleep(0.05)
            beats = [c for c in self.collection.update_one.await_args_list
                     if set(c.args[1]['$set']) == {'updated_at'}]
            self.assertGreaterEqual(len(beats), 2)
            sync.assert_not_called()

            release.set()
            await task
        sync.assert_awaited_once()
        self.assertEqual(self.collection.update_one.await_args.args[1]['$set']['status'], 'done')

    async def test_failed_preparation_fails_the_sync(self):
        sync = AsyncMock(return_value={})
        with patch('services.canvas_submissions_service.sync_course_submissions_direct', sync):
            result = await service.run_tracked_sync(
                'canvas-token', '100', prepare=AsyncMock(side_effect=RuntimeError('Canvas down')))
        self.assertEqual(result['statusCode'], 500)
        sync.assert_not_called()
        self.assertEqual(self.collection.update_one.await_args.args[1]['$set']['status'], 'failed')

    async def test_background_task_is_held_until_done(self):
        release = asyncio.Event()

        async def slow_sync(*args, **kwargs):
            await release.wait()
            return {}

        with patch('services.canvas_submissions_service.sync_course_submissions_direct', slow_sync):
            task = service.start_background_sync('canvas-token', '100')
            self.assertIn(task, service._background_tasks)
            release.set()
            await task
        await asyncio.sleep(0)  # done callbacks run on the next loop pass
        self.assertNotIn(task, service._background_tasks)


if __name__ == '__main__':
    unittest.main()
