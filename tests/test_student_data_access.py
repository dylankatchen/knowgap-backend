import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from services import achieveup_service
from services import analytics_service


def setUpModule():
    # These tests call rate-limited routes more often than the limits allow,
    # and the limiter's counts are shared by every test. The limits have
    # their own tests in test_rate_limits.py.
    from app import app
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


INSTRUCTOR = {'id': 'inst-1', 'role': 'instructor', 'canvasTokenType': 'instructor', 'canvas_student_id': 900}
STUDENT = {'id': 'stu-1', 'role': 'student', 'canvasTokenType': 'student', 'canvas_student_id': 555}
NO_CANVAS_ID = {'id': 'stu-2', 'role': 'student', 'canvasTokenType': 'student', 'canvas_student_id': None}

# Sentinel the analytics roster lookup returns, so a test can tell the
# access check was passed without mocking the whole analytics pipeline.
PAST_ACCESS_CHECK = {'error': 'reached roster lookup', 'statusCode': 418}


class StudentDataAccessTest(unittest.IsolatedAsyncioTestCase):
    """The instructor teaches course '100' now and taught '50' in a past term."""

    def setUp(self):
        self.user = INSTRUCTOR
        self.canvas_checks = []
        self.progress = MagicMock()
        self.progress.find_one = AsyncMock(return_value={
            'student_id': '555', 'course_id': '100', 'skill_progress': {'Loops': {'score': 80}},
            'last_updated': None})
        self.roster = AsyncMock(return_value=PAST_ACCESS_CHECK)

        async def verify_token(token):
            return {'user': self.user}

        async def validate(canvas_token, course_id, include_concluded=False):
            self.canvas_checks.append(course_id)
            if course_id == '100' or (include_concluded and course_id == '50'):
                return {'valid': True}
            return {'valid': False, 'statusCode': 403, 'message': 'Not your course'}

        analytics_db = MagicMock()
        analytics_db.__getitem__.return_value.find.return_value.to_list = AsyncMock(return_value=[])

        for target, value in [
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_service.achieveup_verify_token', verify_token),
            ('services.achieveup_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.validate_canvas_instructor_for_course', validate),
            ('services.achieveup_service.achieveup_progress_collection', self.progress),
            ('services.achieveup_service.get_instructor_course_students', self.roster),
            ('services.analytics_service.db', analytics_db),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # Progress
    async def test_student_reads_own_progress_without_canvas_call(self):
        self.user = STUDENT
        result = await achieveup_service.get_student_progress('t', '555', '100')
        self.assertEqual(result['skill_progress'], {'Loops': {'score': 80}})
        self.assertEqual(self.canvas_checks, [])

    async def test_student_cannot_read_another_students_progress(self):
        self.user = STUDENT
        result = await achieveup_service.get_student_progress('t', '556', '100')
        self.assertEqual(result['statusCode'], 403)
        self.progress.find_one.assert_not_awaited()

    async def test_account_without_canvas_id_matches_nobody(self):
        self.user = NO_CANVAS_ID
        result = await achieveup_service.get_student_progress('t', 'None', '100')
        self.assertEqual(result['statusCode'], 403)
        self.progress.find_one.assert_not_awaited()

    async def test_instructor_reads_progress_in_own_course(self):
        result = await achieveup_service.get_student_progress('t', '555', '100')
        self.assertEqual(result['student_id'], '555')
        self.progress.find_one.assert_awaited_once_with({'student_id': '555', 'course_id': '100'})

    async def test_instructor_reads_progress_in_past_course(self):
        result = await achieveup_service.get_student_progress('t', '555', '50')
        self.assertNotIn('error', result)

    async def test_instructor_denied_progress_in_other_course(self):
        result = await achieveup_service.get_student_progress('t', '555', '999')
        self.assertEqual(result['statusCode'], 403)
        self.progress.find_one.assert_not_awaited()

    # Class analytics
    async def test_analytics_denied_for_student(self):
        self.user = STUDENT
        result = await analytics_service.get_course_students_analytics('t', '100')
        self.assertEqual(result['statusCode'], 403)
        self.roster.assert_not_awaited()

    async def test_analytics_denied_for_other_course(self):
        result = await analytics_service.get_course_students_analytics('t', '999')
        self.assertEqual(result['statusCode'], 403)
        self.roster.assert_not_awaited()

    async def test_analytics_allowed_for_own_course(self):
        result = await analytics_service.get_course_students_analytics('t', '100')
        self.assertEqual(result, PAST_ACCESS_CHECK)

    async def test_analytics_allowed_for_past_course(self):
        result = await analytics_service.get_course_students_analytics('t', '50')
        self.assertEqual(result, PAST_ACCESS_CHECK)

    # Course id format
    async def test_non_numeric_course_ids_rejected_before_canvas(self):
        for course_id in ['.?', '1/../2', '100?x', '12a', '100\n', '', None, '١٢', '１２']:
            with self.subTest(course_id=course_id):
                result = await achieveup_service.check_course_instructor(INSTRUCTOR, course_id)
                self.assertEqual(result['statusCode'], 400)
        self.assertEqual(self.canvas_checks, [])

    async def test_numeric_course_ids_reach_canvas(self):
        self.assertIsNone(await achieveup_service.check_course_instructor(INSTRUCTOR, '100'))
        self.assertIsNone(await achieveup_service.check_course_instructor(INSTRUCTOR, 100))
        self.assertEqual(self.canvas_checks, ['100', '100'])

    # AI skill suggestions
    async def test_skill_suggestions_denied_for_student(self):
        self.user = STUDENT
        with patch.object(achieveup_service.client.chat.completions, 'create',
                          new_callable=AsyncMock) as ai_call:
            result = await achieveup_service.suggest_course_skills_ai('t', {'courseId': '100'})
        self.assertEqual(result['statusCode'], 403)
        ai_call.assert_not_called()


class FakeBadges:
    """Badge collection stand-in supporting {'user_id', 'course_id': {'$in': [...]}} queries."""

    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def find(self, query, projection=None):
        self.queries.append(query)
        matches = [doc for doc in self.docs
                   if doc['user_id'] == query['user_id']
                   and ('course_id' not in query or doc['course_id'] in query['course_id']['$in'])]

        async def results():
            for doc in matches:
                yield dict(doc)
        return results()


class BadgeViewAccessTest(unittest.IsolatedAsyncioTestCase):
    """Student 555 has badges in course '100' (taught by the instructor) and '777' (not)."""

    def setUp(self):
        self.user = INSTRUCTOR
        self.badges = FakeBadges([
            {'user_id': '555', 'course_id': '100', 'badge_id': 'b-100', 'skill_name': 'Loops',
             'earned_at': datetime(2026, 9, 1)},
            {'user_id': '555', 'course_id': '777', 'badge_id': 'b-777', 'skill_name': 'Recursion',
             'earned_at': datetime(2026, 10, 1)},
            {'user_id': '555', 'course_id': '50', 'badge_id': 'b-50', 'skill_name': 'Arrays',
             'earned_at': datetime(2025, 3, 1)},
        ])
        matrices = MagicMock()
        matrices.find_one = AsyncMock(return_value={'course_name': 'Course'})

        async def verify_token(token):
            return {'user': self.user}

        async def validate(canvas_token, course_id, include_concluded=False):
            if course_id == '100' or (include_concluded and course_id == '50'):
                return {'valid': True}
            return {'valid': False, 'statusCode': 403, 'message': 'Not your course'}

        for target, value in [
            ('services.badge_service.achieveup_verify_token', verify_token),
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_auth_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.validate_canvas_instructor_for_course', validate),
            ('services.badge_service.achieveup_user_badges_collection', self.badges),
            ('services.badge_service.achieveup_skill_matrices_collection', matrices),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def view(self, student_id, course_id=None):
        from services.badge_service import get_student_earned_badges
        return await get_student_earned_badges('t', student_id, course_id)

    async def test_student_sees_own_badges_in_every_course(self):
        self.user = STUDENT
        result = await self.view('555')
        self.assertEqual({b['badge_id'] for b in result['badges']}, {'b-100', 'b-777', 'b-50'})

    async def test_instructor_sees_only_the_course_they_teach(self):
        result = await self.view('555', '100')
        self.assertEqual([b['badge_id'] for b in result['badges']], ['b-100'])

    async def test_instructor_sees_badges_in_past_course(self):
        result = await self.view('555', '50')
        self.assertEqual([b['badge_id'] for b in result['badges']], ['b-50'])

    async def test_instructor_denied_for_course_they_dont_teach(self):
        result = await self.view('555', '777')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.badges.queries, [])

    async def test_instructor_must_name_a_course(self):
        result = await self.view('555')
        self.assertEqual(result['statusCode'], 400)
        self.assertEqual(self.badges.queries, [])

    async def test_student_denied_for_another_student(self):
        self.user = STUDENT
        result = await self.view('556', '100')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.badges.queries, [])

    async def test_account_without_canvas_id_matches_nobody(self):
        self.user = NO_CANVAS_ID
        result = await self.view('None')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.badges.queries, [])


class ForceSyncRouteTest(unittest.IsolatedAsyncioTestCase):
    async def force_sync(self, check_result):
        from app import app
        self.sync = AsyncMock()
        with patch('services.achieveup_service.require_course_instructor',
                   AsyncMock(return_value=check_result)) as self.check, \
             patch('services.achieveup_auth_service.get_user_canvas_token',
                   AsyncMock(return_value='canvas-token')), \
             patch('services.canvas_submissions_service.sync_course_submissions_direct', self.sync):
            response = await app.test_client().post(
                '/achieveup/instructor/course/100/force-sync', headers={'Authorization': 'Bearer t'})
            await asyncio.sleep(0)  # let a started background task run
        return response

    async def test_sync_runs_for_course_instructor(self):
        response = await self.force_sync((INSTRUCTOR, None))
        self.assertEqual(response.status_code, 202)
        self.check.assert_awaited_once_with('t', '100', include_concluded=True)
        self.sync.assert_awaited_once_with('canvas-token', '100')

    async def test_sync_refused_when_course_check_fails(self):
        response = await self.force_sync((None, {'error': 'Access denied', 'statusCode': 403}))
        self.assertEqual(response.status_code, 403)
        self.sync.assert_not_called()


if __name__ == '__main__':
    unittest.main()
