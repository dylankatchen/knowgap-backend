import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app import app


def setUpModule():
    # These tests call rate-limited routes more often than the limits allow,
    # and the limiter's counts are shared by every test. The limits have
    # their own tests in test_rate_limits.py.
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


INSTRUCTOR = {'id': 'inst-1', 'role': 'instructor', 'canvasTokenType': 'instructor'}
STUDENT = {'id': 'stu-1', 'role': 'student', 'canvasTokenType': 'student'}
AUTH = {'Authorization': 'Bearer t'}

# Each route, the service it hands off to, and that service's expected arguments.
ROUTES = [
    ('/canvas/instructor/courses',
     'services.achieveup_canvas_service.get_instructor_courses', ('canvas-token',)),
    ('/canvas/instructor/courses/100/quizzes',
     'services.achieveup_canvas_service.get_instructor_course_quizzes', ('canvas-token', '100')),
    ('/canvas/instructor/courses/100/quizzes/7/questions',
     'services.achieveup_canvas_service.get_instructor_quiz_questions', ('canvas-token', '7', '100')),
    ('/achieveup/instructor/dashboard',
     'services.achieveup_service.get_instructor_dashboard', ('t',)),
]
CANVAS_ROUTES = [route for route in ROUTES if route[0].startswith('/canvas/')]


class InstructorRoutesTest(unittest.IsolatedAsyncioTestCase):
    """The instructor course, quiz, question and dashboard routes."""

    def setUp(self):
        self.user = INSTRUCTOR
        self.canvas_token = AsyncMock(return_value='canvas-token')
        self.services = {}

        async def verify_token(token):
            if token != 't':
                return {'error': 'Invalid token', 'message': 'Token is invalid', 'statusCode': 401}
            return {'user': self.user}

        targets = [
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_auth_service.get_user_canvas_token', self.canvas_token),
            # The routes use the app's shared database client; opening a new
            # one per request leaked a connection pool on every call.
            ('motor.motor_asyncio.AsyncIOMotorClient',
             MagicMock(side_effect=AssertionError('routes must not open their own database client'))),
        ]
        for _, service, _ in ROUTES:
            self.services[service] = AsyncMock(return_value={'from': service})
            targets.append((service, self.services[service]))
        for target, value in targets:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_instructor_gets_service_result(self):
        for path, service, args in ROUTES:
            with self.subTest(path=path):
                response = await app.test_client().get(path, headers=AUTH)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(await response.get_json(), {'from': service})
                self.services[service].assert_awaited_once_with(*args)

    async def test_student_is_denied(self):
        self.user = STUDENT
        for path, service, _ in ROUTES:
            with self.subTest(path=path):
                response = await app.test_client().get(path, headers=AUTH)
                self.assertEqual(response.status_code, 403)
                self.services[service].assert_not_awaited()
        self.canvas_token.assert_not_awaited()

    async def test_instructor_role_with_student_canvas_token_is_denied(self):
        self.user = {**INSTRUCTOR, 'canvasTokenType': 'student'}
        for path, service, _ in ROUTES:
            with self.subTest(path=path):
                response = await app.test_client().get(path, headers=AUTH)
                self.assertEqual(response.status_code, 403)
                self.services[service].assert_not_awaited()

    async def test_student_role_with_instructor_canvas_token_is_denied(self):
        # Older signups could leave role 'student' with an instructor Canvas
        # token; like every other instructor route, these need both.
        self.user = {**STUDENT, 'canvasTokenType': 'instructor'}
        for path, service, _ in ROUTES:
            with self.subTest(path=path):
                response = await app.test_client().get(path, headers=AUTH)
                self.assertEqual(response.status_code, 403)
                self.services[service].assert_not_awaited()

    async def test_missing_or_invalid_token_is_rejected(self):
        for path, service, _ in ROUTES:
            for headers in ({}, {'Authorization': 'Bearer wrong'}):
                with self.subTest(path=path, headers=headers):
                    response = await app.test_client().get(path, headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.services[service].assert_not_awaited()

    async def test_instructor_without_canvas_token_gets_400(self):
        self.canvas_token.return_value = None
        for path, service, _ in CANVAS_ROUTES:
            with self.subTest(path=path):
                response = await app.test_client().get(path, headers=AUTH)
                self.assertEqual(response.status_code, 400)
                self.services[service].assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
