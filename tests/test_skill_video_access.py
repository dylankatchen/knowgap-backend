import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from services import skill_video_service
from utils import youtube_utils
from utils.youtube_utils import normalize_youtube_link


def setUpModule():
    # These tests call rate-limited routes more often than the limits allow,
    # and the limiter's counts are shared by every test. The limits have
    # their own tests in test_rate_limits.py.
    from app import app
    limiter_off = patch.dict(app.config, {'QUART_RATE_LIMITER_ENABLED': False})
    limiter_off.start()
    unittest.addModuleCleanup(limiter_off.stop)


VIDEO_ID = 'dQw4w9WgXcQ'
CLEAN_LINK = f'https://www.youtube.com/watch?v={VIDEO_ID}'

INSTRUCTOR = {'id': 'inst-1', 'role': 'instructor', 'canvasTokenType': 'instructor'}
STUDENT = {'id': 'stu-1', 'role': 'student', 'canvasTokenType': 'student'}


class YouTubeLinkTest(unittest.TestCase):
    def test_youtube_video_links_are_kept(self):
        for link in [
            CLEAN_LINK,
            f'http://youtube.com/watch?v={VIDEO_ID}&list=PL1&index=2',
            f'https://m.youtube.com/watch?app=desktop&v={VIDEO_ID}',
            f'https://music.youtube.com/watch?v={VIDEO_ID}&feature=share',
            f'https://youtu.be/{VIDEO_ID}?si=abc',
            f'https://youtu.be/{VIDEO_ID}/',
            f'https://www.youtube.com/shorts/{VIDEO_ID}?si=x',
            f'https://www.youtube.com/embed/{VIDEO_ID}',
            f'https://www.youtube-nocookie.com/embed/{VIDEO_ID}',
            f'https://www.youtube.com/live/{VIDEO_ID}?feature=share',
            f'https://www.youtube.com/v/{VIDEO_ID}',
            f'https://www.youtube.com/watch/?v={VIDEO_ID}',
            f'https://www.youtube.com:443/watch?v={VIDEO_ID}',
            f'HTTPS://WWW.YOUTUBE.COM/watch?v={VIDEO_ID}',
            f'www.youtube.com/watch?v={VIDEO_ID}',
            f'youtu.be/{VIDEO_ID}',
            f'  https://youtu.be/{VIDEO_ID}  ',
            f'https://youtu.be/{VIDEO_ID}?t=0',
            f'https://youtu.be/{VIDEO_ID}?t=abc',
            f'https://youtu.be/{VIDEO_ID}?t=90abc',
            f'https://youtu.be/{VIDEO_ID}?t=' + '9' * 5000,  # too long to be a time
        ]:
            with self.subTest(link=link):
                self.assertEqual(normalize_youtube_link(link), CLEAN_LINK)

    def test_start_time_is_kept(self):
        for link, seconds in [
            (f'https://youtu.be/{VIDEO_ID}?t=90', 90),
            (f'https://www.youtube.com/watch?v={VIDEO_ID}&t=90s', 90),
            (f'https://www.youtube.com/watch?v={VIDEO_ID}&t=1m30s', 90),
            (f'https://www.youtube.com/watch?v={VIDEO_ID}&t=1h2m3s', 3723),
            (f'https://www.youtube.com/embed/{VIDEO_ID}?start=45', 45),
        ]:
            with self.subTest(link=link):
                self.assertEqual(normalize_youtube_link(link), f'{CLEAN_LINK}&t={seconds}s')

    def test_other_links_are_rejected(self):
        for link in [
            'javascript:alert(1)',
            f'JavaScript:alert(document.cookie)//youtube.com/watch?v={VIDEO_ID}',
            f'javascript://youtube.com/watch?v={VIDEO_ID}%0aalert(1)',
            'data:text/html,<script>alert(1)</script>',
            f'ftp://youtube.com/watch?v={VIDEO_ID}',
            f'https://evil.com/watch?v={VIDEO_ID}',
            f'https://youtube.com.evil.com/watch?v={VIDEO_ID}',
            f'https://youtu.be.evil.com/{VIDEO_ID}',
            f'https://youtube.com@evil.com/watch?v={VIDEO_ID}',
            f'https://evil.com/?u=https://youtu.be/{VIDEO_ID}',
            'https://www.youtube.com/redirect?q=https://evil.com',
            'https://www.youtube.com/playlist?list=PL123',
            'https://www.youtube.com/@somechannel',
            'https://www.youtube.com/watch?v=short',
            f'https://www.youtube.com/watch?v={VIDEO_ID}"onmouseover=alert(1)',
            'https://www.youtube.com/watch?v=%3Cscript%3E',
            'https://[::1/watch',
            f'https://evil.com/embed/{VIDEO_ID}',
            f'https://notyoutu.be/{VIDEO_ID}',
            f'https://evilyoutube.com/watch?v={VIDEO_ID}',
            'https://www.youtube.com/user/ABCDEFGHIJK',
            f'https://www.youtube.com/foo/watch?v={VIDEO_ID}',
            'https://www.youtube.com/watch?v=%22%3E%3Cb%3Exxxxxx',  # 11 chars, not an id
            'https://www.youtube.com/watch?v=' + '\u00e9' * 11,
            '', None, 123, {'$ne': None},
        ]:
            with self.subTest(link=link):
                self.assertIsNone(normalize_youtube_link(link))

    def test_parser_tricks_only_ever_produce_a_plain_youtube_link(self):
        # Python and browsers disagree on where this host ends; rebuilding the
        # link from the video id means the stored link is safe either way.
        self.assertEqual(normalize_youtube_link(f'https://evil.com\\@youtube.com/watch?v={VIDEO_ID}'), CLEAN_LINK)


class FakeYouTubeSession:
    """Stands in for aiohttp.ClientSession. `outcome` is the (status, json body)
    YouTube sends back, or an exception raised while asking."""

    def __init__(self, outcome, **kwargs):
        self.outcome = outcome
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def get(self, url):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        status, body = self.outcome
        response = MagicMock(status=status)
        response.json = AsyncMock(return_value=body)
        response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)
        return response


def snippet(**overrides):
    return {'items': [{'snippet': {
        'title': 'Loops &amp; more', 'channelTitle': 'CS Channel',
        'thumbnails': {'high': {'url': 'https://i.ytimg.com/high.jpg'},
                       'medium': {'url': 'https://i.ytimg.com/medium.jpg'}},
        **overrides}}]}


API_KEY = 'secret-api-key'


class VideoMetadataTest(unittest.IsolatedAsyncioTestCase):
    async def lookup(self, outcome):
        sessions = []

        def make_session(**kwargs):
            sessions.append(FakeYouTubeSession(outcome, **kwargs))
            return sessions[-1]
        with patch('aiohttp.ClientSession', make_session):
            result = await youtube_utils.get_video_metadata(CLEAN_LINK)
        return result, sessions[0]

    async def test_video_details_are_returned(self):
        result, session = await self.lookup((200, snippet()))
        self.assertEqual(result, {'title': 'Loops & more', 'link': CLEAN_LINK, 'channel': 'CS Channel',
                                  'thumbnail': 'https://i.ytimg.com/high.jpg'})
        self.assertEqual(session.kwargs['timeout'].total, 10)

    async def test_missing_thumbnail_sizes_fall_back(self):
        result, _ = await self.lookup((200, snippet(thumbnails={'medium': {'url': 'https://i.ytimg.com/medium.jpg'}})))
        self.assertEqual(result['thumbnail'], 'https://i.ytimg.com/medium.jpg')
        result, _ = await self.lookup((200, snippet(thumbnails=None)))
        self.assertEqual(result['thumbnail'], '')

    async def test_unknown_video_is_not_found(self):
        for body in ({'items': []}, {}):
            with self.subTest(body=body):
                result, _ = await self.lookup((200, body))
                self.assertEqual(result, {'error': youtube_utils.VIDEO_NOT_FOUND})

    async def test_youtube_error_reply_gives_its_reason(self):
        quota = {'error': {'code': 403, 'errors': [{'reason': 'quotaExceeded'}]}}
        result, _ = await self.lookup((403, quota))
        self.assertEqual(result, {'error': 'Failed to fetch metadata, status code: 403, reason: quotaExceeded'})
        result, _ = await self.lookup((500, 'not an object'))
        self.assertEqual(result, {'error': 'Failed to fetch metadata, status code: 500, reason: unknown'})

    async def test_failed_lookups_are_logged_instead_of_raising(self):
        for outcome in [
            # aiohttp puts the request URL, API key included, in some errors.
            aiohttp.ClientError(f"url='https://www.googleapis.com/youtube/v3/videos?key={API_KEY}'"),
            aiohttp.ClientConnectionError('no route to host'),
            asyncio.TimeoutError(),
            (200, ['not', 'an', 'object']),
            (200, {'items': [{}]}),
            (200, snippet(title=None)),
        ]:
            with self.subTest(outcome=outcome):
                with self.assertLogs(level='ERROR') as logs:
                    result, _ = await self.lookup(outcome)
                self.assertEqual(result, {'error': 'Failed to fetch metadata'})
                self.assertNotIn(API_KEY, str(logs.output))


class SkillVideoAccessTest(unittest.IsolatedAsyncioTestCase):
    """The instructor currently teaches course '100' and not '999'."""

    def setUp(self):
        self.user = INSTRUCTOR
        self.videos = MagicMock()
        self.videos.insert_one = AsyncMock()
        self.videos.delete_one = AsyncMock()
        self.videos.find_one_and_update = AsyncMock(side_effect=lambda query, update, **kw: {
            '_id': query['_id'], 'course_id': '100', **update['$set']})
        self.stored = {
            'v-100': {'_id': 'v-100', 'course_id': '100', 'source': 'ai_suggested', 'added_by': 'inst-1'},
            'v-50': {'_id': 'v-50', 'course_id': '50', 'source': 'ai_suggested', 'added_by': 'inst-1'},
            'v-999': {'_id': 'v-999', 'course_id': '999', 'source': 'ai_suggested', 'added_by': 'inst-2'},
        }
        self.videos.find_one = AsyncMock(side_effect=lambda query, *a: self.stored.get(query['_id']))
        self.votes = MagicMock()
        self.votes.delete_many = AsyncMock()
        # Course 100 has matrix m-1 (and m-int, saved with a numeric course
        # id); m-999 belongs to another course.
        matrix_docs = [
            {'_id': 'm-1', 'course_id': '100', 'skills': ['Loops'], 'course_name': 'Intro Programming'},
            {'_id': 'm-int', 'course_id': 100, 'skills': ['Loops'], 'course_name': 'Intro Programming'},
            {'_id': 'm-999', 'course_id': '999', 'skills': ['Loops'], 'course_name': 'Other Course'},
        ]

        async def find_matrix(query, projection=None):
            return next((m for m in matrix_docs if all(
                (value in m[key]) if key == 'skills' else m[key] == value
                for key, value in query.items())), None)
        self.matrices = MagicMock()
        self.matrices.find_one = AsyncMock(side_effect=find_matrix)
        self.video_queries = []

        def find_videos(query):
            self.video_queries.append(query)

            async def no_videos():
                return
                yield
            cursor = MagicMock()
            cursor.sort.return_value = no_videos()
            return cursor
        self.videos.find = MagicMock(side_effect=find_videos)

        async def verify_token(token):
            return {'user': self.user}

        async def validate(canvas_token, course_id, include_concluded=False):
            if course_id == '100' or (include_concluded and course_id == '50'):
                return {'valid': True}
            return {'valid': False, 'statusCode': 403, 'message': 'Not your course'}

        for target, value in [
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_service.achieveup_verify_token', verify_token),
            ('services.skill_video_service.achieveup_verify_token', verify_token),
            ('services.achieveup_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.validate_canvas_instructor_for_course', validate),
            ('services.skill_video_service.skill_videos_collection', self.videos),
            ('services.skill_video_service.skill_video_votes_collection', self.votes),
            ('services.skill_video_service.achieveup_skill_matrices_collection', self.matrices),
            ('services.skill_video_service.get_video_metadata', AsyncMock(return_value={
                'title': 'Loops', 'channel': 'CS Channel', 'thumbnail': 'https://i.ytimg.com/x.jpg'})),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def add(self, course_id, link=f'https://youtu.be/{VIDEO_ID}?si=abc'):
        return await skill_video_service.add_skill_video('t', course_id, 'Loops', link, matrix_id='m-1')

    # Add
    async def test_instructor_adds_video_to_own_course(self):
        result = await self.add('100')
        saved = self.videos.insert_one.await_args.args[0]
        self.assertEqual(saved['link'], CLEAN_LINK)
        self.assertEqual(saved['course_id'], '100')
        self.assertEqual(saved['source'], 'manual')
        self.assertEqual(saved['channel'], 'CS Channel')
        self.assertEqual(saved['thumbnail'], 'https://i.ytimg.com/x.jpg')
        self.assertNotIn('added_by', result)

    async def test_add_keeps_the_instructors_title(self):
        await skill_video_service.add_skill_video('t', '100', 'Loops', CLEAN_LINK, title='My title')
        saved = self.videos.insert_one.await_args.args[0]
        self.assertEqual(saved['title'], 'My title')
        self.assertEqual(saved['channel'], 'CS Channel')

    async def test_add_rejects_video_youtube_cannot_find(self):
        with patch('services.skill_video_service.get_video_metadata',
                   AsyncMock(return_value={'error': 'Video not found'})):
            result = await self.add('100')
        self.assertEqual(result['statusCode'], 400)
        self.videos.insert_one.assert_not_awaited()

    async def test_add_saves_nothing_when_youtube_lookup_fails(self):
        with patch('services.skill_video_service.get_video_metadata',
                   AsyncMock(return_value={'error': 'Failed to fetch metadata, status code: 403'})), \
             self.assertLogs('services.skill_video_service', 'ERROR') as logs:
            result = await self.add('100')
        self.assertEqual(result['statusCode'], 502)
        self.assertNotIn('403', result['message'])
        self.assertIn('status code: 403', logs.output[0])
        self.videos.insert_one.assert_not_awaited()

    async def test_add_denied_for_course_not_taught(self):
        result = await self.add('999')
        self.assertEqual(result['statusCode'], 403)
        self.videos.insert_one.assert_not_awaited()

    async def test_add_denied_for_student(self):
        self.user = STUDENT
        result = await self.add('100')
        self.assertEqual(result['statusCode'], 403)
        self.videos.insert_one.assert_not_awaited()

    async def test_add_rejects_non_youtube_link(self):
        result = await self.add('100', link='javascript:alert(document.cookie)')
        self.assertEqual(result['statusCode'], 400)
        self.videos.insert_one.assert_not_awaited()

    async def test_add_denied_for_past_course(self):
        result = await self.add('50')
        self.assertEqual(result['statusCode'], 403)
        self.videos.insert_one.assert_not_awaited()

    async def test_changes_denied_for_past_course_and_for_students(self):
        with patch('services.skill_video_service.fetch_video_transcript') as transcript:
            for user, video_id in [(INSTRUCTOR, 'v-50'), (STUDENT, 'v-100')]:
                self.user = user
                for action in (skill_video_service.remove_skill_video,
                               skill_video_service.verify_ai_video,
                               skill_video_service.find_relevant_moment):
                    with self.subTest(user=user['role'], video=video_id, action=action.__name__):
                        result = await action('t', video_id)
                        self.assertEqual(result['statusCode'], 403)
        self.videos.delete_one.assert_not_awaited()
        self.votes.delete_many.assert_not_awaited()
        self.videos.find_one_and_update.assert_not_awaited()
        transcript.assert_not_called()

    # Matrix ids
    async def test_matrix_from_another_course_is_ignored(self):
        await skill_video_service.add_skill_video('t', '100', 'Loops', CLEAN_LINK, matrix_id='m-999')
        self.assertEqual(self.videos.insert_one.await_args.args[0]['matrix_id'], 'm-1')

        result = await skill_video_service.get_skill_videos('t', '100', 'Loops', 'm-999')
        self.assertEqual(result['matrix_id'], 'm-1')
        self.assertEqual(self.video_queries[-1]['matrix_id'], 'm-1')

    async def suggest(self, matrix_id=None, topics_error='stop here'):
        """Run AI suggestions up to the topic step, which fails with topics_error."""
        topics = AsyncMock(return_value={'success': False, 'error': topics_error})
        descriptions = MagicMock()
        descriptions.find_one = AsyncMock(return_value={'description': 'Course description'})
        mappings = MagicMock()

        async def no_mappings():
            return
            yield
        mappings.find.return_value.limit.return_value = no_mappings()
        with patch('services.skill_video_service.generate_skill_search_topics', topics), \
             patch('services.skill_video_service.achieveup_course_descriptions_collection', descriptions), \
             patch('services.skill_video_service.achieveup_question_skills_collection', mappings):
            result = await skill_video_service.generate_ai_video_recommendations(
                't', '100', 'Loops', matrix_id=matrix_id)
        return result, topics

    async def test_suggest_never_uses_another_courses_matrix(self):
        with self.assertLogs('services.skill_video_service', 'ERROR'):
            _, topics = await self.suggest(matrix_id='m-999')
        course_name = topics.await_args.args[1]
        self.assertEqual(course_name, 'Intro Programming')

    async def test_suggest_logs_ai_error_instead_of_returning_it(self):
        with self.assertLogs('services.skill_video_service', 'ERROR') as logs:
            result, _ = await self.suggest(topics_error='secret AI detail')
        self.assertEqual(result['statusCode'], 502)
        self.assertNotIn('secret AI detail', str(result))
        self.assertIn('secret AI detail', logs.output[0])

    async def test_own_and_unknown_matrix_ids_are_kept(self):
        # 'primary' and deleted matrices have no matrix document, but videos
        # saved under them must still load.
        for matrix_id in ['m-1', 'm-int', 'primary', 'deleted-matrix']:
            with self.subTest(matrix_id=matrix_id):
                result = await skill_video_service.get_skill_videos('t', '100', 'Loops', matrix_id)
                self.assertEqual(result['matrix_id'], matrix_id)

    # Remove
    async def test_instructor_removes_video_in_own_course(self):
        result = await skill_video_service.remove_skill_video('t', 'v-100')
        self.assertTrue(result['success'])
        self.videos.delete_one.assert_awaited_once_with({'_id': 'v-100'})
        self.votes.delete_many.assert_awaited_once_with({'video_id': 'v-100'})

    async def test_remove_denied_for_course_not_taught(self):
        result = await skill_video_service.remove_skill_video('t', 'v-999')
        self.assertEqual(result['statusCode'], 403)
        self.videos.delete_one.assert_not_awaited()
        self.votes.delete_many.assert_not_awaited()

    async def test_remove_missing_video(self):
        result = await skill_video_service.remove_skill_video('t', 'nope')
        self.assertEqual(result['statusCode'], 404)
        self.videos.delete_one.assert_not_awaited()

    # Verify
    async def test_instructor_verifies_video_in_own_course(self):
        result = await skill_video_service.verify_ai_video('t', 'v-100')
        self.assertTrue(result['instructor_verified'])
        self.assertNotIn('added_by', result)

    async def test_verify_denied_for_course_not_taught(self):
        result = await skill_video_service.verify_ai_video('t', 'v-999')
        self.assertEqual(result['statusCode'], 403)
        self.videos.find_one_and_update.assert_not_awaited()

    # Find moment
    async def test_find_moment_denied_for_course_not_taught(self):
        with patch('services.skill_video_service.fetch_video_transcript') as transcript:
            result = await skill_video_service.find_relevant_moment('t', 'v-999')
        self.assertEqual(result['statusCode'], 403)
        transcript.assert_not_called()

    # AI suggestions
    async def test_suggest_denied_for_past_course_other_course_and_students(self):
        with patch('services.skill_video_service.generate_skill_search_topics') as topics:
            for user, course_id in [(INSTRUCTOR, '50'), (INSTRUCTOR, '999'), (STUDENT, '100')]:
                self.user = user
                with self.subTest(user=user['role'], course_id=course_id):
                    result = await skill_video_service.generate_ai_video_recommendations('t', course_id, 'Loops')
                    self.assertEqual(result['statusCode'], 403)
        topics.assert_not_called()
        self.videos.insert_many.assert_not_called()

    # Preferred channels (read)
    async def test_channels_readable_in_current_and_past_course_only(self):
        from services import achieveup_service
        with patch('services.achieveup_service.get_saved_course_channels',
                   AsyncMock(return_value=[{'channel_id': 'c1', 'name': 'CS'}])) as saved:
            for course_id in ['100', '50']:
                with self.subTest(course_id=course_id):
                    self.assertEqual(await achieveup_service.get_course_channels('t', course_id),
                                     [{'channel_id': 'c1', 'name': 'CS'}])
            result = await achieveup_service.get_course_channels('t', '999')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(saved.await_count, 2)


class SkillVideoRouteInputTest(unittest.IsolatedAsyncioTestCase):
    async def post(self, path, body, service_name):
        from app import app
        with patch(f'routes.skill_video_routes.{service_name}', AsyncMock(return_value={'ok': True})) as service:
            response = await app.test_client().post(path, json=body, headers={'Authorization': 'Bearer t'})
        return response, service

    async def test_text_values_reach_the_service(self):
        for path, body, service_name in [
            ('/achieveup/skill-videos/get', {'course_id': '100', 'skill_name': 'Loops'}, 'get_skill_videos'),
            ('/achieveup/skill-videos/get', {'course_id': '100', 'skill_name': 'Loops', 'matrix_id': 'm-1'}, 'get_skill_videos'),
            ('/achieveup/skill-videos', {'course_id': '100', 'skill_name': 'Loops', 'link': CLEAN_LINK, 'title': 'x'}, 'add_skill_video'),
            ('/achieveup/skill-videos/suggest', {'course_id': '100', 'skill_name': 'Loops'}, 'generate_ai_video_recommendations'),
            ('/achieveup/skill-videos/vote', {'video_id': 'v-100', 'vote_type': 'upvote'}, 'vote_skill_video'),
        ]:
            with self.subTest(path=path, body=body):
                response, service = await self.post(path, body, service_name)
                self.assertEqual(response.status_code, 201 if path == '/achieveup/skill-videos' else 200)
                service.assert_awaited_once()

    async def test_each_field_rejects_objects_and_lists(self):
        add_body = {'course_id': '100', 'skill_name': 'Loops', 'link': CLEAN_LINK}
        for path, base, fields, service_name in [
            ('/achieveup/skill-videos/get', {'course_id': '100', 'skill_name': 'Loops'},
             ['course_id', 'skill_name', 'matrix_id'], 'get_skill_videos'),
            ('/achieveup/skill-videos', add_body,
             ['course_id', 'skill_name', 'link', 'matrix_id', 'title'],
             'add_skill_video'),
            ('/achieveup/skill-videos/suggest', {'course_id': '100', 'skill_name': 'Loops'},
             ['course_id', 'skill_name', 'matrix_id'], 'generate_ai_video_recommendations'),
            ('/achieveup/skill-videos/vote', {'video_id': 'v-100', 'vote_type': 'upvote'},
             ['video_id', 'vote_type'], 'vote_skill_video'),
        ]:
            for field in fields:
                for bad_value in ({'$ne': None}, ['x']):
                    with self.subTest(path=path, field=field, value=bad_value):
                        response, service = await self.post(path, {**base, field: bad_value}, service_name)
                        self.assertEqual(response.status_code, 400)
                        service.assert_not_called()

    async def test_add_ignores_caller_channel_thumbnail_and_source(self):
        body = {'course_id': '100', 'skill_name': 'Loops', 'link': CLEAN_LINK, 'title': 'x',
                'channel': 'Evil', 'thumbnail': 'javascript:alert(1)', 'source': 'ai_suggested'}
        response, service = await self.post('/achieveup/skill-videos', body, 'add_skill_video')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(service.await_args.kwargs, {'matrix_id': None, 'title': 'x'})

    async def test_edit_route_is_gone(self):
        from app import app
        response = await app.test_client().put(
            '/achieveup/skill-videos/v-100', json={'link': 'javascript:alert(1)'}, headers={'Authorization': 'Bearer t'})
        self.assertEqual(response.status_code, 405)


if __name__ == '__main__':
    unittest.main()
