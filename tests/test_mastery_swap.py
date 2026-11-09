import asyncio
import unittest

import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch

from services import canvas_submissions_service as sync_service
from services import mastery_service


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length=None):
        return self.docs


# Question q1 tests Loops; q2 tests Loops and Recursion.
QUESTION_SKILLS = [
    {'question_id': 'q1', 'skills': ['Loops'], 'matrix_id': 'm1'},
    {'question_id': 'q2', 'skills': ['Loops', 'Recursion'], 'matrix_id': 'm1'},
]


def submission(student_id, answers):
    return {'student_id': student_id, 'student_name': f'Student {student_id}', 'course_id': '100',
            'questions': [{'question_id': q, 'correct': c} for q, c in answers]}


class MasteryTallyTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        question_skills = MagicMock()
        question_skills.find = MagicMock(side_effect=lambda query: FakeCursor(QUESTION_SKILLS))
        patcher = patch.object(mastery_service, 'question_skills_collection', question_skills)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.mastery = MagicMock()
        self.mastery.bulk_write = AsyncMock()
        self.mastery.delete_many = AsyncMock()
        patcher = patch.object(mastery_service, 'mastery_collection', self.mastery)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.award = AsyncMock()
        patcher = patch.object(mastery_service, 'check_and_award_badge', self.award)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_totals_add_up_across_quizzes(self):
        tally = mastery_service.CourseMasteryTally()
        await tally.add_submission(submission('s1', [('q1', True), ('q2', False)]))
        await tally.add_submission(submission('s1', [('q1', True)]))
        self.assertEqual(tally.totals[('s1', 'Loops', 'm1')], {'correct': 2, 'total': 3})
        self.assertEqual(tally.totals[('s1', 'Recursion', 'm1')], {'correct': 0, 'total': 1})

    async def test_nothing_is_written_until_the_swap(self):
        tally = mastery_service.CourseMasteryTally()
        await tally.add_submission(submission('s1', [('q1', True)]))
        self.mastery.bulk_write.assert_not_called()
        self.mastery.delete_many.assert_not_called()
        self.award.assert_not_called()

    async def test_swap_sets_final_totals_then_removes_old_rows(self):
        tally = mastery_service.CourseMasteryTally()
        await tally.add_submission(submission('s1', [('q1', True), ('q2', False)]))
        await mastery_service.replace_course_mastery('100', 'Data Structures', tally)

        operations = self.mastery.bulk_write.await_args.args[0]
        updates = {op._filter['skill_id']: op._doc['$set'] for op in operations}
        self.assertEqual(updates['Loops']['total_correct'], 1)
        self.assertEqual(updates['Loops']['total_attempted'], 2)
        self.assertEqual(updates['Loops']['mastery_percentage'], 50)
        # Totals are set, never incremented, so a re-sync can't double-count.
        self.assertTrue(all('$inc' not in op._doc for op in operations))

        sync_id = updates['Loops']['sync_id']
        self.mastery.delete_many.assert_awaited_once_with({'course_id': '100', 'sync_id': {'$ne': sync_id}})

    async def test_badges_use_the_final_score_not_the_first_quiz(self):
        # A perfect first quiz followed by a failed one is 50%, not 100%.
        tally = mastery_service.CourseMasteryTally()
        await tally.add_submission(submission('s1', [('q1', True)]))
        await tally.add_submission(submission('s1', [('q1', False)]))
        await mastery_service.replace_course_mastery('100', 'Data Structures', tally)
        self.award.assert_awaited_once_with('s1', '100', 'Loops', 50, 'Student s1', 'Data Structures')


class SyncSwapTest(unittest.IsolatedAsyncioTestCase):
    """The sync builds new scores off to the side and swaps them in at the end."""

    on_progress = None
    session_get = None
    add_submission_error = None

    def setUp(self):
        # Retries wait between tries; don't make the tests wait.
        patcher = patch.object(sync_service, 'RETRY_BASE_DELAY', 0)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def run_sync(self, quiz_results, submissions=None):
        self.replace = AsyncMock()
        self.add_submission = AsyncMock(side_effect=self.add_submission_error)
        tally = MagicMock()
        tally.add_submission = self.add_submission
        mastery = MagicMock()
        mastery.delete_many = AsyncMock()
        mastery.count_documents = AsyncMock(return_value=0)
        mastery.find = MagicMock(return_value=FakeCursor([]))
        quizzes = [{'id': f'quiz{i}', 'title': f'Quiz {i}'} for i in range(len(quiz_results))]

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        if self.session_get:
            session.get = self.session_get
        with patch.object(sync_service, 'get_instructor_course_quizzes', AsyncMock(return_value=quizzes)), \
             patch.object(sync_service, 'get_all_course_submissions',
                          submissions or AsyncMock(side_effect=quiz_results)), \
             patch.object(sync_service, 'create_canvas_session', MagicMock(return_value=session)), \
             patch.object(sync_service, 'process_submission_data', AsyncMock(side_effect=lambda sub: dict(sub))), \
             patch.object(sync_service, 'store_submission_data', AsyncMock(return_value=True)), \
             patch.object(sync_service, 'achieveup_skill_matrices_collection', MagicMock(update_many=AsyncMock())), \
             patch('services.mastery_service.CourseMasteryTally', MagicMock(return_value=tally)), \
             patch('services.mastery_service.replace_course_mastery', self.replace), \
             patch('services.mastery_service.mastery_collection', mastery):
            result = await sync_service.sync_course_submissions_direct(
                'canvas-token', '100', 'Data Structures', on_progress=self.on_progress)
        self.mastery = mastery
        return result, tally

    async def test_scores_are_swapped_in_once_after_every_quiz(self):
        quiz_results = [
            {'submissions': [{'user_id': 's1', 'questions': []}]},
            {'submissions': [{'user_id': 's2', 'questions': []}]},
        ]
        result, tally = await self.run_sync(quiz_results)
        self.assertEqual(result['message'], 'Sync completed (Direct)')
        self.assertEqual(self.add_submission.await_count, 2)
        self.replace.assert_awaited_once_with('100', 'Data Structures', tally)
        # The live scores are never erased up front.
        self.mastery.delete_many.assert_not_called()

    async def test_quizzes_run_several_at_a_time_up_to_the_limit(self):
        running = 0
        peak = 0

        async def slow_quiz(token, course_id, quiz_id):
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.01)
            running -= 1
            return {'submissions': []}

        progress = []
        self.on_progress = AsyncMock(side_effect=lambda done, total: progress.append((done, total)))
        await self.run_sync([None] * 10, submissions=slow_quiz)

        self.assertEqual(peak, sync_service.QUIZ_CONCURRENCY)
        # Reported once up front, then once as each quiz finishes.
        self.assertEqual(progress[0], (0, 10))
        self.assertEqual(progress[-1], (10, 10))
        self.assertEqual(len(progress), 11)

    async def test_one_quiz_crashing_counts_as_its_error_and_others_still_sync(self):
        results = iter([RuntimeError('boom'), {'submissions': [{'user_id': 's1', 'questions': []}]}])

        async def quiz(token, course_id, quiz_id):
            result = next(results)
            if isinstance(result, Exception):
                raise result
            return result

        result, tally = await self.run_sync([None, None], submissions=quiz)
        self.assertEqual(result['total_errors'], 1)
        self.assertEqual(self.add_submission.await_count, 1)
        # The other quiz was read, but its scores alone aren't swapped in.
        self.assert_previous_scores_kept(result)

    def assert_previous_scores_kept(self, result):
        self.assertEqual(result['error'], 'Sync incomplete')
        self.assertIn('left as they were', result['message'])
        self.replace.assert_not_called()
        self.mastery.delete_many.assert_not_called()

    async def test_previous_scores_kept_when_one_quiz_fails_partway(self):
        quiz_results = [
            {'submissions': [{'user_id': 's1', 'questions': []}]},
            {'error': 'Failed to fetch submissions: 503'},
            {'submissions': [{'user_id': 's2', 'questions': []}]},
        ]
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(result['total_errors'], 1)
        self.assert_previous_scores_kept(result)

    @staticmethod
    def canvas_response(status, body=None):
        response = MagicMock(status=status, headers={})
        response.json = AsyncMock(return_value=body)
        response.text = AsyncMock(return_value='')
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)
        return response

    async def test_previous_scores_kept_when_a_submissions_answers_cannot_be_read(self):
        self.session_get = MagicMock(return_value=self.canvas_response(503))
        quiz_results = [
            {'submissions': [{'user_id': 's1', 'questions': []}]},
            {'submissions': [{'user_id': 's2', 'id': 'sub2'}]},
        ]
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(result['failed_submissions'], 1)
        # Tried once, then retried before giving up.
        self.assertEqual(self.session_get.call_count, sync_service.CANVAS_RETRIES + 1)
        self.assert_previous_scores_kept(result)

    async def test_a_brief_canvas_failure_is_retried_and_the_sync_completes(self):
        self.session_get = MagicMock(side_effect=[
            self.canvas_response(503),
            self.canvas_response(200, {'quiz_submission_questions': []}),
        ])
        quiz_results = [{'submissions': [{'user_id': 's1', 'id': 'sub1'}]}]
        result, tally = await self.run_sync(quiz_results)
        self.assertEqual(result['message'], 'Sync completed (Direct)')
        self.assertEqual(self.session_get.call_count, 2)
        self.replace.assert_awaited_once_with('100', 'Data Structures', tally)

    async def test_a_dropped_connection_is_retried(self):
        self.session_get = MagicMock(side_effect=[
            aiohttp.ClientConnectionError('reset'),
            self.canvas_response(200, {'quiz_submission_questions': []}),
        ])
        quiz_results = [{'submissions': [{'user_id': 's1', 'id': 'sub1'}]}]
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(result['message'], 'Sync completed (Direct)')

    async def test_an_error_a_retry_cannot_fix_is_not_retried(self):
        self.session_get = MagicMock(return_value=self.canvas_response(403))
        quiz_results = [{'submissions': [{'user_id': 's1', 'id': 'sub1'}]}]
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(self.session_get.call_count, 1)
        self.assert_previous_scores_kept(result)

    async def test_previous_scores_kept_when_a_submission_cannot_be_tallied(self):
        quiz_results = [{'submissions': [{'user_id': 's1', 'questions': []},
                                         {'user_id': 's2', 'questions': []}]}]
        self.add_submission_error = RuntimeError('db down')
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(result['total_errors'], 1)
        self.assert_previous_scores_kept(result)

    async def test_previous_scores_kept_when_no_quiz_could_be_read(self):
        quiz_results = [{'error': 'Canvas is down'}, {'error': 'Canvas is down'}]
        result, _ = await self.run_sync(quiz_results)
        self.assertEqual(result['total_errors'], 2)
        self.replace.assert_not_called()
        self.mastery.delete_many.assert_not_called()


if __name__ == '__main__':
    unittest.main()
