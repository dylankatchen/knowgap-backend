import unittest
from unittest.mock import AsyncMock, patch

# Spaces and capitals must reach the service as sent: the check only rejects
# values that aren't text, it doesn't clean them up.
EMAIL = ' Ann@UCF.edu '

SIGNUP = {'name': 'Ann', 'email': EMAIL, 'password': 'Passw0rd!',
          'canvasApiToken': 'canvas-token', 'canvasTokenType': 'instructor'}
LOGIN = {'email': EMAIL, 'password': 'Passw0rd!'}
PROFILE = {'name': 'Ann', 'email': EMAIL, 'canvasApiToken': 'canvas-token',
           'canvasTokenType': 'instructor'}

ROUTES = [
    ('post', '/auth/signup', SIGNUP, 'achieveup_signup'),
    ('post', '/auth/login', LOGIN, 'achieveup_login'),
    ('put', '/auth/profile', PROFILE, 'achieveup_update_profile'),
]


class AuthRouteInputTest(unittest.IsolatedAsyncioTestCase):
    async def send(self, method, path, body, service_name):
        from app import app
        with patch(f'routes.auth_routes.{service_name}', AsyncMock(return_value={'ok': True})) as service:
            response = await getattr(app.test_client(), method)(
                path, json=body, headers={'Authorization': 'Bearer t'})
        return response, service

    async def test_text_values_reach_the_service_unchanged(self):
        expected_args = {
            '/auth/signup': ('Ann', EMAIL, 'Passw0rd!', 'canvas-token', 'instructor'),
            '/auth/login': (EMAIL, 'Passw0rd!'),
            '/auth/profile': ('t', 'Ann', EMAIL, 'canvas-token', 'instructor'),
        }
        for method, path, body, service_name in ROUTES:
            with self.subTest(path=path):
                response, service = await self.send(method, path, {**body, 'extra': {'$ne': None}}, service_name)
                self.assertEqual(response.status_code, 201 if path == '/auth/signup' else 200)
                self.assertEqual(service.await_args.args, expected_args[path])

    async def test_optional_fields_can_be_missing_or_null(self):
        for method, path, body, service_name in [
            ('post', '/auth/signup', {**SIGNUP, 'canvasTokenType': None}, 'achieveup_signup'),
            ('put', '/auth/profile', {'name': 'Ann', 'email': EMAIL}, 'achieveup_update_profile'),
            ('put', '/auth/profile', {'name': 'Ann', 'email': EMAIL, 'canvasApiToken': ''},
             'achieveup_update_profile'),
        ]:
            with self.subTest(path=path, body=body):
                response, service = await self.send(method, path, body, service_name)
                self.assertLess(response.status_code, 300)
                service.assert_awaited_once()

    async def test_each_field_rejects_objects_lists_and_numbers(self):
        for method, path, body, service_name in ROUTES:
            for field in body:
                for bad_value in ({'$regex': '^a'}, {'$ne': None}, ['x'], 5, True):
                    with self.subTest(path=path, field=field, value=bad_value):
                        response, service = await self.send(method, path, {**body, field: bad_value}, service_name)
                        self.assertEqual(response.status_code, 400)
                        self.assertEqual((await response.get_json())['message'], 'Request fields must be text')
                        service.assert_not_called()

    async def test_body_that_is_not_an_object_is_rejected(self):
        for method, path, _, service_name in ROUTES:
            for bad_body in (['x'], 'text', 5):
                with self.subTest(path=path, body=bad_body):
                    response, service = await self.send(method, path, bad_body, service_name)
                    self.assertEqual(response.status_code, 400)
                    service.assert_not_called()

    async def test_missing_fields_keep_their_messages(self):
        for method, path, body, service_name, message in [
            ('post', '/auth/signup', {**SIGNUP, 'email': ''}, 'achieveup_signup',
             'Name, email, password, and canvas API token are required.'),
            ('post', '/auth/login', {'email': EMAIL}, 'achieveup_login', 'Email and password are required'),
            ('put', '/auth/profile', {'name': 'Ann'}, 'achieveup_update_profile', 'Name and email are required'),
        ]:
            with self.subTest(path=path):
                response, service = await self.send(method, path, body, service_name)
                self.assertEqual(response.status_code, 400)
                self.assertEqual((await response.get_json())['message'], message)
                service.assert_not_called()


if __name__ == '__main__':
    unittest.main()
