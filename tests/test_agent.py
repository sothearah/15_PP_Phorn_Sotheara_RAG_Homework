"""Offline agent-loop tests: no API calls and no registration data writes."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import agent


def call(name='search_course', arguments='{"query": "AI"}', call_id='call_1'):
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            pass
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def response(*calls, text='Done', status='completed'):
    return SimpleNamespace(message=SimpleNamespace(role='assistant', tool_calls=list(calls), content=text), done=status == 'completed', done_reason='stop')


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(agent, 'load_dotenv', lambda *args: None)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('OLLAMA_MODEL', 'llama3.2:latest')
    client = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = client
    monkeypatch.setattr(agent, 'Client', factory)
    return client


def result_from(client):
    history = client.chat.call_args.kwargs['messages']
    return json.loads([item for item in history if isinstance(item, dict) and item.get('role') == 'tool'][-1]['content'])


@pytest.mark.parametrize('name,arguments,role', [
    ('search_course', '{"query":"AI"}', 'student'),
    ('check_schedule', '{"student_id":"S1001"}', 'student'),
    ('register_course', '{"student_id":"S1001","course_id":"AI201"}', 'admin'),
])
def test_routes_through_harness(setup, monkeypatch, name, arguments, role):
    schema, _ = agent.TOOL_ROUTES[name]
    function = MagicMock(return_value={'status': 'success'})
    monkeypatch.setitem(agent.TOOL_ROUTES, name, (schema, function))
    setup.chat.side_effect = [response(call(name, arguments)), response(text='Finished')]
    assert agent.StudentAssistantAgent(role=role).run('Help') == 'Finished'
    assert isinstance(function.call_args.args[0], schema)
    assert result_from(setup)['status'] == 'success'
    sent_tools = setup.chat.call_args.kwargs['tools']
    for sent, original in zip(sent_tools, agent.TOOL_DEFINITIONS):
        assert sent['function'] == {key: original[key] for key in ('name', 'description', 'parameters')}
    assert setup.chat.call_args.kwargs['model'] == 'llama3.2:latest'


def test_student_registration_denied(setup, monkeypatch):
    schema, _ = agent.TOOL_ROUTES['register_course']
    function = MagicMock()
    monkeypatch.setitem(agent.TOOL_ROUTES, 'register_course', (schema, function))
    setup.chat.side_effect = [
        response(call('register_course', '{"student_id":"S1001","course_id":"WEB220"}')),
        response(text='Permission denied'),
    ]
    assert agent.StudentAssistantAgent().run('Register me') == 'Permission denied'
    function.assert_not_called()
    assert result_from(setup)['error'] == 'permission_denied'


@pytest.mark.parametrize('name,arguments,error', [
    ('unknown', '{}', 'unknown_tool'),
    ('search_course', '{', 'invalid_arguments'),
    ('search_course', '{}', 'invalid_arguments'),
    ('search_course', '[]', 'invalid_arguments'),
    ('search_course', '{"query":123}', 'invalid_arguments'),
    ('search_course', '{"query":"AI","role":"admin"}', 'invalid_arguments'),
])
def test_bad_calls_are_controlled(setup, name, arguments, error):
    setup.chat.side_effect = [response(call(name, arguments)), response()]
    agent.StudentAssistantAgent().run('Help')
    assert result_from(setup)['error'] == error


def test_tool_failure_is_controlled(setup, monkeypatch):
    schema, _ = agent.TOOL_ROUTES['search_course']
    monkeypatch.setitem(agent.TOOL_ROUTES, 'search_course', (schema, MagicMock(side_effect=OSError('private path'))))
    setup.chat.side_effect = [response(call()), response()]
    agent.StudentAssistantAgent().run('Help')
    assert result_from(setup) == {'status': 'error', 'error': 'tool_execution_failed'}


def test_iteration_limit_prevents_last_turn_execution(setup, monkeypatch):
    execute = MagicMock()
    monkeypatch.setattr(agent.StudentAssistantAgent, '_execute_tool', execute)
    setup.chat.return_value = response(call())
    assert 'iteration limit' in agent.StudentAssistantAgent(max_iterations=1).run('Help')
    execute.assert_not_called()


def test_invalid_calls_count_toward_limit(setup):
    setup.chat.return_value = response(call('unknown', '{}'))
    assert 'tool-call limit' in agent.StudentAssistantAgent(max_tool_calls=1).run('Help')
    assert setup.chat.call_count == 2


def test_multiple_calls_keep_names_and_assistant_message(setup):
    setup.chat.side_effect = [response(call('unknown_one', '{}'), call('unknown_two', '{}')), response()]
    agent.StudentAssistantAgent().run('Help')
    history = setup.chat.call_args.kwargs['messages']
    assert history[2].role == 'assistant'
    assert len(history[2].tool_calls) == 2
    assert [x['tool_name'] for x in history if isinstance(x, dict) and x.get('role') == 'tool'] == ['unknown_one', 'unknown_two']


def test_each_run_has_fresh_limits(setup):
    setup.chat.side_effect = [response(call('unknown', '{}')), response(), response(call('unknown', '{}')), response()]
    assistant = agent.StudentAssistantAgent(max_tool_calls=1)
    assert assistant.run('First') == 'Done'
    assert assistant.run('Second') == 'Done'


def test_api_error_is_controlled(setup):
    setup.chat.side_effect = agent.ResponseError('secret detail')
    answer = agent.StudentAssistantAgent().run('Help')
    assert 'Ollama request failed' in answer
    assert 'secret detail' not in answer


@pytest.mark.parametrize('status,text,expected', [('incomplete', '', 'did not complete'), ('completed', '', 'no final answer')])
def test_empty_or_incomplete_response(setup, status, text, expected):
    setup.chat.return_value = response(status=status, text=text)
    assert expected in agent.StudentAssistantAgent().run('Help')


def test_default_model_without_api_key(setup, monkeypatch):
    monkeypatch.delenv('OLLAMA_MODEL')
    setup.chat.return_value = response()
    assert agent.StudentAssistantAgent().run('Help') == 'Done'
    assert setup.chat.call_args.kwargs['model'] == 'llama3.2:latest'


def test_empty_request(setup):
    assert 'non-empty' in agent.StudentAssistantAgent().run('  ')
    setup.chat.assert_not_called()


@pytest.mark.parametrize('error', [ConnectionError('private detail'), agent.HTTPError('private detail'), ValueError('malformed response')])
def test_ollama_connection_and_response_errors(setup, error):
    setup.chat.side_effect = error
    answer = agent.StudentAssistantAgent().run('Help')
    assert 'Ollama request failed' in answer
    assert 'private detail' not in answer


def test_real_ollama_response_shape(setup):
    from ollama import ChatResponse
    setup.chat.side_effect = [
        ChatResponse(model='llama3.2:latest', done=True, message={
            'role': 'assistant', 'content': '',
            'tool_calls': [{'function': {'name': 'search_course', 'arguments': {'query': 'AI'}}}],
        }),
        ChatResponse(model='llama3.2:latest', done=True, message={
            'role': 'assistant', 'content': 'Found AI201',
        }),
    ]
    assert agent.StudentAssistantAgent().run('Find me an AI course.') == 'Found AI201'
    assert result_from(setup)['courses'][0]['course_id'] == 'AI201'


@pytest.mark.parametrize('registration_status', ['success', 'already_registered'])
def test_registration_then_schedule_continues(setup, monkeypatch, registration_status):
    from copy import deepcopy
    from ollama import ChatResponse

    prompt = 'Register S1002 for WEB220, then show the updated schedule for S1002.'
    registration = {'status': registration_status, 'student_id': 'S1002', 'course_id': 'WEB220'}
    schedule = {'status': 'success', 'student_id': 'S1002', 'schedule': [{'course_id': 'WEB220'}]}
    execution_order = []

    def register(request):
        assert request.student_id == 'S1002'
        assert request.course_id == 'WEB220'
        execution_order.append('register_course')
        return registration

    def check(request):
        assert request.student_id == 'S1002'
        execution_order.append('check_schedule')
        return schedule

    monkeypatch.setitem(agent.TOOL_ROUTES, 'register_course', (agent.RegisterCourseInput, register))
    monkeypatch.setitem(agent.TOOL_ROUTES, 'check_schedule', (agent.CheckScheduleInput, check))
    snapshots = []

    def model_reply(**kwargs):
        # Snapshot at request time: later appends must not mask missing history.
        snapshots.append(deepcopy(kwargs))
        turn = len(snapshots)
        if turn == 3:
            return ChatResponse(done=True, message={'role': 'assistant', 'content': 'S1002: WEB220'})
        name = 'register_course' if turn == 1 else 'check_schedule'
        arguments = {'student_id': 'S1002'}
        if turn == 1:
            arguments['course_id'] = 'WEB220'
        return ChatResponse(done=True, message={
            'role': 'assistant', 'content': '',
            'tool_calls': [{'function': {'name': name, 'arguments': arguments}}],
        })

    setup.chat.side_effect = model_reply
    assert agent.StudentAssistantAgent(role='admin').run(prompt) == 'S1002: WEB220'
    assert execution_order == ['register_course', 'check_schedule']
    assert [len(item['messages']) for item in snapshots] == [2, 4, 6]
    for item in snapshots:
        assert item['messages'][1] == {'role': 'user', 'content': prompt}
        assert item['tools'] == snapshots[0]['tools']
    assert snapshots[1]['messages'][2].tool_calls[0].function.name == 'register_course'
    assert json.loads(snapshots[1]['messages'][3]['content']) == registration
    assert snapshots[2]['messages'][4].tool_calls[0].function.name == 'check_schedule'
    assert snapshots[2]['messages'][5]['tool_name'] == 'check_schedule'
    assert json.loads(snapshots[2]['messages'][5]['content']) == schedule


@pytest.mark.parametrize('debug', [True, False])
def test_debug_output_is_optional(setup, capsys, debug):
    setup.chat.side_effect = [response(call('unknown', {'query': 'AI'})), response()]
    assert agent.StudentAssistantAgent(debug=debug).run('Help') == 'Done'
    captured = capsys.readouterr()
    assert captured.out == ''
    if debug:
        assert 'iteration 1/3' in captured.err
        assert 'iteration 2/3' in captured.err
        assert 'requested tool: unknown' in captured.err
        assert 'arguments: {"query": "AI"}' in captured.err
        assert 'tool result: {"status": "error", "error": "unknown_tool"}' in captured.err
    else:
        assert captured.err == ''
