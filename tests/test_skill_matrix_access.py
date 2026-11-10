import unittest
from unittest.mock import AsyncMock, patch

from services import achieveup_canvas_service as canvas_service
from services import achieveup_service

INSTRUCTOR = {'id': 'inst-1', 'role': 'instructor', 'canvasTokenType': 'instructor'}
STUDENT = {'id': 'stu-1', 'role': 'student', 'canvasTokenType': 'student'}


class FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs


class FakeCollection:
    """In-memory stand-in for the matrices collection (exact-match queries only)."""

    def __init__(self, docs=()):
        self.docs = {doc['_id']: dict(doc) for doc in docs}

    def _matches(self, query):
        return [doc for doc in self.docs.values()
                if all(doc.get(key) == value for key, value in query.items())]

    async def find_one(self, query):
        matches = self._matches(query)
        return dict(matches[0]) if matches else None

    def find(self, query):
        return FakeCursor([dict(doc) for doc in self._matches(query)])

    async def insert_one(self, doc):
        self.docs[doc['_id']] = dict(doc)

    async def update_one(self, query, update):
        matches = self._matches(query)
        for doc in matches:
            doc.update(update['$set'])
        return type('Result', (), {'matched_count': len(matches)})()

    async def delete_one(self, query):
        matches = self._matches(query)
        for doc in matches[:1]:
            del self.docs[doc['_id']]
        return type('Result', (), {'deleted_count': len(matches[:1])})()


def matrix(matrix_id, course_id, name='Matrix'):
    return {'_id': matrix_id, 'course_id': course_id, 'matrix_name': name, 'skills': ['Skill A']}


class SkillMatrixAccessTest(unittest.IsolatedAsyncioTestCase):
    """The instructor teaches course '100' now and taught '50' in a past term."""

    def setUp(self):
        self.matrices = FakeCollection([matrix('m-own', '100'), matrix('m-other', '999'),
                                        matrix('m-past', '50', 'Old Matrix')])
        self.import_status = AsyncMock()
        self.canvas_status = None
        self.user = INSTRUCTOR

        async def verify_token(token):
            return {'user': self.user}

        async def validate(canvas_token, course_id, include_concluded=False):
            if self.canvas_status:
                return {'valid': False, 'statusCode': self.canvas_status, 'message': 'Canvas down'}
            if course_id == '100' or (include_concluded and course_id == '50'):
                return {'valid': True}
            return {'valid': False, 'statusCode': 403, 'message': 'Not your course'}

        for target, value in [
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.validate_canvas_instructor_for_course', validate),
            ('services.achieveup_service.achieveup_skill_matrices_collection', self.matrices),
            ('services.achieveup_service.achieveup_import_status_collection', self.import_status),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # Create
    async def test_create_in_own_course(self):
        result = await achieveup_service.create_skill_matrix('t', '100', 'New', ['S'])
        self.assertEqual(result['course_id'], '100')
        self.assertEqual(result['created_by'], 'inst-1')
        self.assertIn(result['_id'], self.matrices.docs)

    async def test_create_denied_for_other_course(self):
        result = await achieveup_service.create_skill_matrix('t', '999', 'New', ['S'])
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)

    async def test_create_denied_for_past_course(self):
        result = await achieveup_service.create_skill_matrix('t', '50', 'New', ['S'])
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)

    async def test_create_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.create_skill_matrix('t', '100', 'New', ['S'])
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)

    # Update
    async def test_update_own_matrix(self):
        result = await achieveup_service.update_skill_matrix('t', 'm-own', ['B'], 'Renamed')
        self.assertEqual(result['matrix_name'], 'Renamed')
        self.assertEqual(self.matrices.docs['m-own']['skills'], ['B'])

    async def test_update_denied_for_other_course(self):
        result = await achieveup_service.update_skill_matrix('t', 'm-other', ['B'], 'Hijacked')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.matrices.docs['m-other']['matrix_name'], 'Matrix')

    async def test_update_denied_for_past_course(self):
        result = await achieveup_service.update_skill_matrix('t', 'm-past', ['B'], 'Renamed')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.matrices.docs['m-past']['matrix_name'], 'Old Matrix')

    async def test_update_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.update_skill_matrix('t', 'm-own', ['B'], 'Hijacked')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(self.matrices.docs['m-own']['matrix_name'], 'Matrix')

    async def test_update_missing_matrix(self):
        result = await achieveup_service.update_skill_matrix('t', 'nope', ['B'], 'X')
        self.assertEqual(result['statusCode'], 404)

    async def test_update_canvas_outage_is_not_a_denial(self):
        self.canvas_status = 502
        result = await achieveup_service.update_skill_matrix('t', 'm-own', ['B'], 'Renamed')
        self.assertEqual(result['statusCode'], 502)
        self.assertEqual(self.matrices.docs['m-own']['matrix_name'], 'Matrix')

    # Delete
    async def test_delete_own_matrix(self):
        result = await achieveup_service.delete_skill_matrix('t', 'm-own')
        self.assertEqual(result, {'success': True})
        self.assertNotIn('m-own', self.matrices.docs)

    async def test_delete_denied_for_other_course(self):
        result = await achieveup_service.delete_skill_matrix('t', 'm-other')
        self.assertEqual(result['statusCode'], 403)
        self.assertIn('m-other', self.matrices.docs)

    async def test_delete_denied_for_past_course(self):
        result = await achieveup_service.delete_skill_matrix('t', 'm-past')
        self.assertEqual(result['statusCode'], 403)
        self.assertIn('m-past', self.matrices.docs)

    async def test_delete_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.delete_skill_matrix('t', 'm-own')
        self.assertEqual(result['statusCode'], 403)
        self.assertIn('m-own', self.matrices.docs)

    async def test_delete_missing_matrix(self):
        result = await achieveup_service.delete_skill_matrix('t', 'nope')
        self.assertEqual(result['statusCode'], 404)

    # List by course
    async def test_list_own_course(self):
        result = await achieveup_service.get_all_skill_matrices_by_course('t', '100')
        self.assertEqual([m['_id'] for m in result['matrices']], ['m-own'])

    async def test_list_past_course_allowed(self):
        result = await achieveup_service.get_all_skill_matrices_by_course('t', '50')
        self.assertEqual([m['_id'] for m in result['matrices']], ['m-past'])

    async def test_list_denied_for_other_course(self):
        result = await achieveup_service.get_all_skill_matrices_by_course('t', '999')
        self.assertEqual(result['statusCode'], 403)
        self.assertNotIn('matrices', result)

    async def test_list_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.get_all_skill_matrices_by_course('t', '100')
        self.assertEqual(result['statusCode'], 403)

    # Import
    async def test_import_from_past_course(self):
        result = await achieveup_service.import_matrices_from_course('50', '100', 'inst-1', 't')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['course_id'], '100')
        self.assertEqual(result[0]['matrix_name'], 'Old Matrix (Imported Skills Matrix)')
        self.assertEqual(result[0]['created_by'], 'inst-1')
        self.import_status.update_one.assert_awaited_once()

    async def test_import_denied_from_other_course(self):
        result = await achieveup_service.import_matrices_from_course('999', '100', 'inst-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)
        self.import_status.update_one.assert_not_awaited()

    async def test_import_denied_into_other_course(self):
        result = await achieveup_service.import_matrices_from_course('50', '999', 'inst-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)
        self.import_status.update_one.assert_not_awaited()

    async def test_import_denied_into_past_course(self):
        result = await achieveup_service.import_matrices_from_course('100', '50', 'inst-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)
        self.import_status.update_one.assert_not_awaited()

    async def test_import_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.import_matrices_from_course('50', '100', 'stu-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.assertEqual(len(self.matrices.docs), 3)
        self.import_status.update_one.assert_not_awaited()

    # AI question analysis
    async def analyze(self, course_id, matrix_id):
        self.ai = AsyncMock(return_value=[])
        with patch('services.achieveup_ai_service.analyze_questions', self.ai):
            return await achieveup_service.analyze_questions_with_ai(
                't', [{'id': 'q1', 'text': 'Q'}], course_id, matrix_id)

    async def test_analyze_with_own_matrix(self):
        result = await self.analyze('100', 'm-own')
        self.assertEqual(result['course_skills_used'], ['Skill A'])
        self.ai.assert_awaited_once()

    async def test_analyze_ignores_matrix_from_other_course(self):
        self.matrices.docs['m-other']['skills'] = ['Secret Skill']
        result = await self.analyze('100', 'm-other')
        # Falls back to the caller's own course matrix, as for a missing ID.
        self.assertEqual(result['course_skills_used'], ['Skill A'])
        self.assertNotIn(['Secret Skill'], [call.args[1] for call in self.ai.await_args_list])

    async def test_analyze_denied_for_other_course(self):
        result = await self.analyze('999', 'm-other')
        self.assertEqual(result['statusCode'], 403)
        self.ai.assert_not_awaited()

    async def test_analyze_denied_for_past_course(self):
        result = await self.analyze('50', 'm-past')
        self.assertEqual(result['statusCode'], 403)
        self.ai.assert_not_awaited()

    async def test_analyze_denied_for_student(self):
        self.user = STUDENT
        result = await self.analyze('100', 'm-own')
        self.assertEqual(result['statusCode'], 403)
        self.ai.assert_not_awaited()


class SkillMappingAccessTest(unittest.IsolatedAsyncioTestCase):
    """Same course setup as SkillMatrixAccessTest: '100' current, '50' past."""

    def setUp(self):
        self.question_skills = AsyncMock()
        self.import_status = AsyncMock()
        self.user = INSTRUCTOR

        async def verify_token(token):
            return {'user': self.user}

        async def validate(canvas_token, course_id, include_concluded=False):
            if course_id == '100' or (include_concluded and course_id == '50'):
                return {'valid': True}
            return {'valid': False, 'statusCode': 403, 'message': 'Not your course'}

        quizzes = AsyncMock(return_value=[{'id': 1, 'title': 'Quiz 1'}])
        questions = AsyncMock(return_value=[{'id': 7, 'question_text': 'What is 2+2?'}])
        self.canvas_quizzes = quizzes
        for target, value in [
            ('services.achieveup_auth_service.achieveup_verify_token', verify_token),
            ('services.achieveup_auth_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.get_user_canvas_token', AsyncMock(return_value='canvas-token')),
            ('services.achieveup_service.validate_canvas_instructor_for_course', validate),
            ('services.achieveup_service.achieveup_question_skills_collection', self.question_skills),
            ('services.achieveup_service.achieveup_import_status_collection', self.import_status),
            ('services.achieveup_canvas_service.get_instructor_course_quizzes', quizzes),
            ('services.achieveup_canvas_service.get_instructor_quiz_questions', questions),
            ('services.achieveup_service.get_assigned_skills',
             AsyncMock(return_value={'question_skills': {'7': ['Addition']}})),
        ]:
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def saved_mappings(self):
        """(owner_id, course_id, skills) for each mapping written."""
        return [(call.args[1]['$set']['owner_id'], call.args[1]['$addToSet']['course_ids'],
                 call.args[1]['$set']['skills'])
                for call in self.question_skills.update_one.await_args_list]

    # Save
    async def test_assign_in_own_course(self):
        result = await achieveup_service.assign_skills_to_questions('t', '100', {'Q1': ['S']})
        self.assertEqual(result, {'message': 'Skills assigned successfully'})
        self.assertEqual(self.saved_mappings(), [('inst-1', '100', ['S'])])

    async def test_assign_denied_for_other_course(self):
        result = await achieveup_service.assign_skills_to_questions('t', '999', {'Q1': ['S']})
        self.assertEqual(result['statusCode'], 403)
        self.question_skills.update_one.assert_not_awaited()

    async def test_assign_denied_for_past_course(self):
        result = await achieveup_service.assign_skills_to_questions('t', '50', {'Q1': ['S']})
        self.assertEqual(result['statusCode'], 403)
        self.question_skills.update_one.assert_not_awaited()

    async def test_assign_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.assign_skills_to_questions('t', '100', {'Q1': ['S']})
        self.assertEqual(result['statusCode'], 403)
        self.question_skills.update_one.assert_not_awaited()

    async def test_assign_accepts_everything_the_assignment_page_sends(self):
        # Questions with no skills are sent as empty lists.
        mappings = {'Q1': ['Loops', 'Recursion'], 'Q2': [], 'Q3': ['A skill with spaces & symbols!']}
        result = await achieveup_service.assign_skills_to_questions('t', '100', mappings)
        self.assertEqual(result, {'message': 'Skills assigned successfully'})
        self.assertEqual(len(self.saved_mappings()), 3)

    async def test_assign_rejects_malformed_mappings(self):
        for mappings in [
            ['Q1'],                                   # not question -> skills pairs
            {'Q1': 'Loops'},                          # skills not a list
            {'Q1': ['Loops', {'$ne': None}]},         # object would act as a database operator
            {'Q1': [{'id': 's1', 'name': 'Loops'}]},  # object would crash mastery
            {'Q1': [None]},
            {'Q1': [7]},
        ]:
            with self.subTest(mappings=mappings):
                result = await achieveup_service.assign_skills_to_questions('t', '100', mappings)
                self.assertEqual(result['statusCode'], 400)
        self.question_skills.update_one.assert_not_awaited()

    async def test_assign_checks_access_before_input(self):
        result = await achieveup_service.assign_skills_to_questions('t', '999', {'Q1': [None]})
        self.assertEqual(result['statusCode'], 403)

    # Skills import
    async def test_skills_import_from_past_course(self):
        result = await achieveup_service.import_skill_setting_from_course('50', '100', 'inst-1', 't')
        self.assertEqual(result['imported_count'], 1)
        self.assertEqual(self.saved_mappings(), [('inst-1', '100', ['Addition'])])
        self.import_status.update_one.assert_awaited_once()

    async def test_skills_import_denied_into_other_course(self):
        result = await achieveup_service.import_skill_setting_from_course('50', '999', 'inst-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.canvas_quizzes.assert_not_awaited()
        self.question_skills.update_one.assert_not_awaited()
        self.import_status.update_one.assert_not_awaited()

    async def test_skills_import_denied_into_past_course(self):
        result = await achieveup_service.import_skill_setting_from_course('100', '50', 'inst-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.question_skills.update_one.assert_not_awaited()
        self.import_status.update_one.assert_not_awaited()

    async def test_skills_import_denied_for_student(self):
        self.user = STUDENT
        result = await achieveup_service.import_skill_setting_from_course('50', '100', 'stu-1', 't')
        self.assertEqual(result['statusCode'], 403)
        self.question_skills.update_one.assert_not_awaited()
        self.import_status.update_one.assert_not_awaited()


class InstructorDashboardTest(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_returns_no_matrices(self):
        matrices = AsyncMock()
        students = [{'id': '1'}, {'id': '2'}]
        with patch('services.achieveup_service.achieveup_verify_token',
                   AsyncMock(return_value={'user': INSTRUCTOR})), \
             patch('services.achieveup_auth_service.get_user_canvas_token',
                   AsyncMock(return_value='canvas-token')), \
             patch('services.achieveup_canvas_service.get_instructor_courses',
                   AsyncMock(return_value=[{'id': '100'}])), \
             patch('services.achieveup_canvas_service.get_course_students',
                   AsyncMock(return_value=students)), \
             patch('services.achieveup_service.achieveup_skill_matrices_collection', matrices):
            result = await achieveup_service.get_instructor_dashboard('t')

        self.assertEqual(set(result), {'courses', 'students', 'totalCourses', 'lastUpdated'})
        self.assertEqual(result['students'], 2)
        self.assertEqual(matrices.mock_calls, [])


class FakeResponse:
    def __init__(self, status, json_payload):
        self.status = status
        self._json_payload = json_payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        return self._json_payload


class FakeSession:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None, params=None):
        self.calls.append(params)
        if url.endswith('/users/self'):
            return FakeResponse(200, {'id': 7})
        return FakeResponse(200, [{'type': 'TeacherEnrollment'}])


class CourseInstructorStateFilterTest(unittest.IsolatedAsyncioTestCase):
    async def check_state_sent(self, expected_state, **kwargs):
        calls = []
        with patch('services.achieveup_canvas_service.create_canvas_session',
                   side_effect=lambda: FakeSession(calls)):
            result = await canvas_service.validate_canvas_instructor_for_course('tok', '100', **kwargs)
        self.assertTrue(result['valid'])
        self.assertEqual(calls[-1]['state[]'], expected_state)

    async def test_default_requires_active_enrollment(self):
        await self.check_state_sent('active')

    async def test_include_concluded_also_accepts_past_terms(self):
        await self.check_state_sent('current_and_concluded', include_concluded=True)


if __name__ == '__main__':
    unittest.main()
