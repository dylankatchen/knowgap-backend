import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services import achieveup_service
from utils import youtube_utils

SECRET = 'secret internal detail'


class ErrorMessageTest(unittest.IsolatedAsyncioTestCase):
    """Unexpected errors are logged on the server, and the client only gets a
    generic message."""

    def assertNoDetail(self, payload):
        self.assertNotIn(SECRET, str(payload))

    async def test_import_routes_hide_exception_text(self):
        from app import app
        failing = AsyncMock(side_effect=Exception(SECRET))
        with patch('services.achieveup_auth_service.achieveup_verify_token', failing), \
             patch('services.achieveup_service.get_import_status', failing), \
             self.assertLogs('routes.achieveup_routes', 'ERROR') as logs:
            for method, path in [
                ('post', '/achieveup/matrix/import'),
                ('post', '/achieveup/skills/import'),
                ('get', '/achieveup/import-status/100'),
            ]:
                with self.subTest(path=path):
                    response = await getattr(app.test_client(), method)(
                        path, json={}, headers={'Authorization': 'Bearer t'})
                    self.assertEqual(response.status_code, 500)
                    body = await response.get_json()
                    self.assertEqual(body['message'], 'An unexpected error occurred')
                    self.assertNoDetail(body)
        self.assertEqual(sum(SECRET in line for line in logs.output), 3)

    async def test_auth_routes_hide_exception_text(self):
        from app import app
        failing = AsyncMock(side_effect=Exception(SECRET))
        routes = [
            ('post', '/auth/signup', {'name': 'Ann', 'email': 'a@b.c', 'password': 'Passw0rd!',
                                      'canvasApiToken': 't'}, 'routes.auth_routes.achieveup_signup'),
            ('post', '/auth/login', {'email': 'a@b.c', 'password': 'Passw0rd!'},
             'routes.auth_routes.achieveup_login'),
            ('get', '/auth/me', None, 'routes.auth_routes.achieveup_verify_token'),
            ('put', '/auth/profile', {'name': 'Ann', 'email': 'a@b.c'},
             'routes.auth_routes.achieveup_update_profile'),
            ('put', '/auth/password', {'currentPassword': 'a', 'newPassword': 'b'},
             'routes.auth_routes.achieveup_change_password'),
            ('post', '/auth/validate-canvas-token', {'canvasApiToken': 'x' * 64},
             'services.achieveup_canvas_service.validate_canvas_token'),
        ]
        with self.assertLogs('routes.auth_routes', 'ERROR') as logs:
            for method, path, body, target in routes:
                with self.subTest(path=path), patch(target, failing):
                    response = await getattr(app.test_client(), method)(
                        path, json=body, headers={'Authorization': 'Bearer t'})
                    self.assertEqual(response.status_code, 500)
                    body = await response.get_json()
                    self.assertEqual(body['message'], 'An unexpected error occurred')
                    self.assertNoDetail(body)
        self.assertEqual(sum(SECRET in line for line in logs.output), len(routes))

    async def test_skill_suggestions_hide_exception_text(self):
        with patch('services.achieveup_service.require_instructor', AsyncMock(side_effect=Exception(SECRET))), \
             patch('traceback.print_exc'), \
             self.assertLogs('services.achieveup_service', 'ERROR') as logs:
            result = await achieveup_service.suggest_course_skills_ai('t', {})
        self.assertEqual(result['statusCode'], 500)
        self.assertNoDetail(result)
        self.assertIn(SECRET, logs.output[0])

    async def test_skills_import_hides_exception_text(self):
        with patch('services.achieveup_service.require_course_instructor', AsyncMock(side_effect=Exception(SECRET))), \
             patch('traceback.print_exc'), \
             self.assertLogs('services.achieveup_service', 'ERROR') as logs:
            result = await achieveup_service.import_skill_setting_from_course('1', '2', 'u', 't')
        self.assertEqual(result['statusCode'], 500)
        self.assertNoDetail(result)
        self.assertIn(SECRET, logs.output[0])

    async def test_transcript_error_hides_exception_text(self):
        api = MagicMock()
        api.return_value.fetch.side_effect = Exception(SECRET)
        with patch('utils.youtube_utils.YouTubeTranscriptApi', api), self.assertLogs(level='ERROR') as logs:
            result = await youtube_utils.fetch_video_transcript('dQw4w9WgXcQ')
        self.assertEqual(result, {'success': False, 'error': 'Failed to fetch transcript'})
        self.assertIn(SECRET, logs.output[0])


if __name__ == '__main__':
    unittest.main()
