import unittest
from unittest.mock import patch

from services import achieveup_canvas_service as canvas_service


class FakeResponse:
    def __init__(self, status, json_payload=None, text_payload='', headers=None):
        self.status = status
        self._json_payload = json_payload if json_payload is not None else []
        self._text_payload = text_payload
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json_payload

    async def text(self):
        return self._text_payload


class FakeSession:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def get(self, url, headers=None, params=None):
        self.calls.append({'url': url, 'params': params})
        if not self._responses:
            raise RuntimeError('No fake responses left for request')
        return self._responses.pop(0)


class FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestInstructorCoursesPagination(unittest.IsolatedAsyncioTestCase):
    async def test_get_instructor_courses_fetches_all_pages(self):
        first_page_courses = [
            {'id': i, 'name': f'Course {i}', 'course_code': f'C-{i}', 'enrollment_term_id': 'term-1'}
            for i in range(1, 101)
        ]
        second_page_courses = [
            {'id': i, 'name': f'Course {i}', 'course_code': f'C-{i}', 'enrollment_term_id': 'term-1'}
            for i in range(101, 151)
        ]

        first_response = FakeResponse(
            200,
            json_payload=first_page_courses,
            headers={
                'Link': '<https://webcourses.ucf.edu/api/v1/courses?page=2&per_page=100>; rel="next", '
                        '<https://webcourses.ucf.edu/api/v1/courses?page=2&per_page=100>; rel="last"'
            },
        )
        second_response = FakeResponse(200, json_payload=second_page_courses)
        fake_session = FakeSession([first_response, second_response])

        with patch.object(canvas_service.Config, 'ENABLE_DEMO_MODE', False), patch(
            'services.achieveup_canvas_service.create_canvas_session',
            return_value=FakeSessionContext(fake_session),
        ):
            result = await canvas_service.get_instructor_courses('fake-token')

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 150)
        self.assertEqual(result[0]['id'], '1')
        self.assertEqual(result[-1]['id'], '150')

        self.assertEqual(len(fake_session.calls), 2)
        self.assertEqual(fake_session.calls[0]['params'], {'enrollment_type': 'teacher', 'per_page': 100})
        self.assertIsNone(fake_session.calls[1]['params'])

    async def test_get_instructor_courses_returns_error_response(self):
        error_response = FakeResponse(401, text_payload='Unauthorized')
        fake_session = FakeSession([error_response])

        with patch.object(canvas_service.Config, 'ENABLE_DEMO_MODE', False), patch(
            'services.achieveup_canvas_service.create_canvas_session',
            return_value=FakeSessionContext(fake_session),
        ):
            result = await canvas_service.get_instructor_courses('fake-token')

        self.assertEqual(result['statusCode'], 401)
        self.assertIn('Failed to fetch instructor courses', result['error'])


if __name__ == '__main__':
    unittest.main()
