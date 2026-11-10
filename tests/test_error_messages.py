import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from services import achieveup_service
from utils import youtube_utils


def setUpModule():
    # These tests call rate-limited routes more often than the limits allow,
    # and the limiter's counts are shared by every test. The limits have
    # their own tests in test_rate_limits.py.
    from app import app
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


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
                ('get', '/achieveup/import-status/100'),
            ]:
                with self.subTest(path=path):
                    response = await getattr(app.test_client(), method)(
                        path, json={}, headers={'Authorization': 'Bearer t'})
                    self.assertEqual(response.status_code, 500)
                    body = await response.get_json()
                    self.assertEqual(body['message'], 'An unexpected error occurred')
                    self.assertNoDetail(body)
        self.assertEqual(sum(SECRET in line for line in logs.output), 2)

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
        # Token validation needs a login, so the caller is logged in for every
        # route; /auth/me's own patch below makes the login check itself fail.
        logged_in = AsyncMock(return_value={'user': {'id': 'u1'}})
        with self.assertLogs('routes.auth_routes', 'ERROR') as logs, \
             patch('routes.auth_routes.achieveup_verify_token', logged_in):
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
        with patch('services.achieveup_service.require_course_instructor', AsyncMock(side_effect=Exception(SECRET))), \
             patch('traceback.print_exc'), \
             self.assertLogs('services.achieveup_service', 'ERROR') as logs:
            result = await achieveup_service.suggest_course_skills_ai('t', {})
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
