import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def setUpModule():
    from app import app
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


ROUTES = [
    ('/canvas/instructor/courses',
     'services.achieveup_canvas_service.get_instructor_courses'),
    ('/canvas/instructor/courses/100/quizzes',
     'services.achieveup_canvas_service.get_instructor_course_quizzes'),
    ('/canvas/instructor/courses/100/quizzes/7/questions',
     'services.achieveup_canvas_service.get_instructor_quiz_questions'),
]


class InstructorCanvasErrorTest(unittest.IsolatedAsyncioTestCase):
    """Canvas errors reach the client with an error status, not a 200 whose
    body happens to be an error dict."""

    def setUp(self):
        # Instructor in both the token and the users collection, so the test
        # passes whichever one the route checks.
        users = MagicMock()
        users.find_one = AsyncMock(return_value={'user_id': 'u1', 'canvas_token_type': 'instructor'})
        db = MagicMock()
        db.__getitem__.return_value = users
        client = MagicMock()
        client.__getitem__.return_value = db
        for target, value in [
            ('services.achieveup_auth_service.achieveup_verify_token',
             AsyncMock(return_value={'user': {'id': 'u1', 'role': 'instructor',
                                              'canvasTokenType': 'instructor'}})),
            ('services.achieveup_auth_service.get_user_canvas_token',
             AsyncMock(return_value='canvas-token')),
            ('motor.motor_asyncio.AsyncIOMotorClient', MagicMock(return_value=client)),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def get(self, path, target, result):
        from app import app
        with patch(target, AsyncMock(return_value=result)):
            response = await app.test_client().get(path, headers={'Authorization': 'Bearer t'})
        return response.status_code, await response.get_json()

    async def test_canvas_outage_is_502(self):
        for path, target in ROUTES:
            with self.subTest(path=path):
                status, body = await self.get(path, target, {'error': 'Failed to fetch instructor courses: 503', 'statusCode': 503})
                self.assertEqual(status, 502)
                self.assertEqual(body['statusCode'], 502)
                self.assertIn('503', body['error'])
                self.assertTrue(body['message'])

    async def test_rejected_canvas_token_is_400_not_401(self):
        # A 401 would make the frontend log the user out of AchieveUp.
        for path, target in ROUTES:
            with self.subTest(path=path):
                status, _ = await self.get(path, target, {'error': 'Invalid Canvas token', 'statusCode': 401})
                self.assertEqual(status, 400)

    async def test_other_errors_keep_their_status(self):
        for path, target in ROUTES:
            for code, error in [(404, 'Not found'), (500, 'Internal server error')]:
                with self.subTest(path=path, code=code):
                    status, body = await self.get(path, target, {'error': error, 'statusCode': code})
                    self.assertEqual(status, code)
                    self.assertEqual(body['error'], error)

    async def test_success_is_200_with_list(self):
        for path, target in ROUTES:
            with self.subTest(path=path):
                status, body = await self.get(path, target, [{'id': '1'}])
                self.assertEqual(status, 200)
                self.assertEqual(body, [{'id': '1'}])


if __name__ == '__main__':
    unittest.main()
