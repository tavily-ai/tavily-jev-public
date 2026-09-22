import asyncio
from copy import deepcopy

import httpx
import pytest

from backend import providers as p
from backend.defaults import DEFAULT_COMPANY
from backend.models import Company


@pytest.mark.parametrize('verdict,confidence,importance,baseline', [
    ('Alert', .34, 'high', False),
    ('Ignore', .2, 'high', False),
    ('Alert', .99, 'watch', False),
    ('Alert', .99, 'off', False),
    ('Alert', .99, 'high', True),
    ('Watch', .1, 'high', True),
])
def test_jev_decision_is_never_overridden(monkeypatch, verdict, confidence, importance, baseline):
    company = Company(**DEFAULT_COMPANY)
    company.priorities[0].importance = importance
    probabilities = {label: .56 if label == verdict else .22 for label in ('Alert', 'Watch', 'Ignore')}
    async def evaluate(*args):
        return {'model': 'jev-test', 'answers': {
            'triage': {'choice': verdict, 'confidence': confidence, 'probabilities': probabilities},
            'priority': {'choice': 'ai'}, 'reason': {'choice': 'priority_match'},
        }}, 123
    monkeypatch.setattr(p, 'evaluate', evaluate)
    result = asyncio.run(p.classify({'title': 'Source', 'content': 'Retrieved passage', 'baseline': baseline}, company))
    assert result['verdict'] == verdict
    assert result['confidence'] == confidence
    assert result['probabilities'] == probabilities
    assert not result.get('policy')


def test_jev_receives_only_context_source_and_unqualified_labels(monkeypatch):
    company = Company(**DEFAULT_COMPANY)
    source = {'title': 'Source title', 'content': 'Retrieved passage', 'url': 'https://example.com/update', 'published_date': '2026-09-21'}
    captured = {}
    async def evaluate(state, questions):
        captured.update(state=state, questions=questions)
        return {'model': 'jev-test', 'answers': {
            'triage': {'choice': 'Alert', 'confidence': .34, 'probabilities': {'Alert': .56, 'Watch': .43, 'Ignore': .01}},
            'priority': {'choice': 'ai'}, 'reason': {'choice': 'priority_match'},
        }}, 123
    monkeypatch.setattr(p, 'evaluate', evaluate)
    asyncio.run(p.classify({**source, 'baseline': True, 'kind': 'Current snapshot', 'retrieval_score': .9}, company))
    assert captured['state'] == {'company': company.model_dump(), 'source': source}
    assert captured['questions'] == {'triage': {
        'type': 'choice', 'instructions': 'How important is this source for this company?',
        'criteria': {'Alert': None, 'Watch': None, 'Ignore': None},
    }}


def test_tavily_sdk_options_dedup_and_cache(monkeypatch):
    calls = []
    class FakeTavily:
        def __init__(self, **kwargs):
            assert kwargs['client_name'] == 'jev-tavily-signal-desk'
        async def search(self, **kwargs):
            calls.append(kwargs)
            return {'request_id': 'test-request', 'results': [{'title':'A launch','url':'https://notion.so/update?utm_source=test','content':'A concrete update','score':.9}, {'title':'Duplicate','url':'https://notion.so/update','content':'Same source'}]}
        async def close(self):
            pass
    monkeypatch.setattr(p, 'AsyncTavilyClient', FakeTavily)
    monkeypatch.setenv('TAVILY_API_KEY', 'test-key')
    p._cache.clear()
    company = Company(**{**DEFAULT_COMPANY, 'competitors': [{'name': 'Notion', 'domain': 'notion.so'}]})
    async def exercise():
        items, warnings, traces = await p.collect(company, 'day')
        assert len(items) == 1 and not warnings
        assert items[0]['url'] == 'https://notion.so/update'
        assert len(traces) == 2
        await p.collect(company, 'day')
    asyncio.run(exercise())
    assert len(calls) == 2  # Same searches reuse the ten-minute cache.
    for call in calls:
        assert call['search_depth'] == 'advanced'
        assert call['include_answer'] is False
        assert call['include_raw_content'] is False
        assert call['max_results'] == 4
        assert len(call['query']) < 400
    news = next(c for c in calls if c['topic'] == 'news')
    assert news['time_range'] == 'day'
    baseline = next(c for c in calls if c['topic'] == 'general')
    assert baseline['include_domains'] == ['notion.so']
    assert 'time_range' not in baseline
    p._cache.clear()


def test_official_jev_contract_and_invalid_response(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test-jev-key')
    original = httpx.AsyncClient
    captured = []
    def handle(request):
        import json
        assert str(request.url) == 'https://api.typesafe.ai/v1/systemone'
        assert request.headers['Authorization'] == 'Bearer test-jev-key'
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'model':'jev-test','answers':{'triage':{'type':'choice','choice':'Watch','confidence':.8,'probabilities':{'Alert':.1,'Watch':.8,'Ignore':.1}}}})
    monkeypatch.setattr(p.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    q = {'triage': p.choice('Triage this source', {'Alert':'Act','Watch':'Review','Ignore':'Skip'})}
    result, latency = asyncio.run(p.evaluate({'source':'Example'}, q))
    assert result['answers']['triage']['choice'] == 'Watch'
    assert captured[0]['questions']['triage']['criteria']['Watch'] == 'Review'
    assert captured[0]['model'] == 'jev-latest'
    q['triage']['criteria'] = {'Unexpected':'Something else'}
    with pytest.raises(p.ProviderError, match='unexpected response'):
        asyncio.run(p.evaluate({},q))


def test_jev_failure_does_not_invent_a_classification(monkeypatch):
    from backend import app as app_module
    from fastapi.testclient import TestClient
    monkeypatch.setenv('TAVILY_API_KEY', 'test')
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test')
    async def collect(*args):
        return [{'id':'real-source','synthetic':False}], [], []
    async def classify(*args):
        raise p.ProviderError('Jev unavailable')
    monkeypatch.setattr(app_module,'collect',collect)
    monkeypatch.setattr(app_module,'classify',classify)
    import json
    r=TestClient(app_module.app).post('/api/scan',json={'mode':'live','company':DEFAULT_COMPANY})
    events=[json.loads(line) for line in r.text.splitlines()]
    assert any(e['type']=='source_error' and e['id']=='real-source' and e['message']=='Jev unavailable' for e in events)
    assert not any(e['type']=='decision' for e in events)
    assert events[-1]['failed'] == 1



def test_names_only_watchlist_searches_without_domain_filter(monkeypatch):
    calls = []
    async def search(query, **kwargs):
        calls.append(kwargs)
        return {'cached': False, 'results': [{'title': 'Linear product update', 'url': 'https://linear.app/changelog', 'content': 'A product announcement.'}]}
    monkeypatch.setattr(p, 'search', search)
    company = Company(**{**DEFAULT_COMPANY, 'competitors': [{'name': 'Linear'}]})
    items, warnings, traces = asyncio.run(p.collect(company, 'week'))
    assert len(calls) == 2 and not warnings
    assert all('include_domains' not in call for call in calls)
    assert next(call for call in calls if call['topic'] == 'news')['time_range'] == 'week'
    assert items[0]['competitor'] == 'Linear'
    assert items[0]['source_type'] == 'Web coverage'
    assert len(traces) == 2
