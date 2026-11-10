import unittest
from unittest.mock import AsyncMock, patch


def setUpModule():
    # These tests call rate-limited routes more often than the limits allow,
    # and the limiter's counts are shared by every test. The limits have
    # their own tests in test_rate_limits.py.
    from app import app
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


CANVAS_TOKEN = 'x' * 64
VALID = {'valid': True, 'message': 'Token is valid',
         'user_info': {'id': 77, 'name': 'Ann Lee', 'email': 'ann@ucf.edu'},
         'permissions': {'student': True, 'instructor': False}}


class CanvasTokenValidationTest(unittest.IsolatedAsyncioTestCase):

    async def validate(self, headers, verify_result=None, body=None):
        from app import app
        self.canvas = AsyncMock(return_value=VALID)
        verify = AsyncMock(return_value=verify_result or {'user': {'id': 'u1'}})
        with patch('routes.auth_routes.achieveup_verify_token', verify), \
             patch('services.achieveup_canvas_service.validate_canvas_token', self.canvas):
            return await app.test_client().post(
                '/auth/validate-canvas-token',
                json={'canvasApiToken': CANVAS_TOKEN} if body is None else body,
                headers=headers)

    async def test_needs_login(self):
        response = await self.validate({})
        self.assertEqual(response.status_code, 401)
        self.canvas.assert_not_awaited()

    async def test_rejects_invalid_login(self):
        expired = {'error': 'Token expired', 'statusCode': 401}
        response = await self.validate({'Authorization': 'Bearer old'}, expired)
        self.assertEqual(response.status_code, 401)
        self.canvas.assert_not_awaited()

    async def test_rejects_fields_that_are_not_text(self):
        for body in (['x'], {'canvasApiToken': 5}, {'canvasApiToken': CANVAS_TOKEN, 'canvasTokenType': {}}):
            with self.subTest(body=body):
                response = await self.validate({'Authorization': 'Bearer t'}, body=body)
                self.assertEqual(response.status_code, 400)
                self.canvas.assert_not_awaited()

    async def test_returns_only_the_verdict(self):
        response = await self.validate({'Authorization': 'Bearer t'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(await response.get_json(), {'valid': True, 'message': 'Token is valid'})
        self.canvas.assert_awaited_once_with(CANVAS_TOKEN, 'student')


if __name__ == '__main__':
    unittest.main()
