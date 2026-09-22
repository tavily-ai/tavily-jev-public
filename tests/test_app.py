import json

from fastapi.testclient import TestClient
import pytest

from backend.app import app
from backend.defaults import DEFAULT_COMPANY
from backend.models import Company
from backend.providers import canonical_url

client = TestClient(app)


def test_no_live_fallback_without_keys(monkeypatch):
    for key in ['TAVILY_API_KEY', 'TYPESAFE_API_KEY', 'JEV_API_KEY']:
        monkeypatch.delenv(key, raising=False)
    response = client.post('/api/scan', json={'company': DEFAULT_COMPANY})
    assert response.status_code == 503
    assert 'Connect' in response.json()['detail']


def test_foreign_origins_cannot_change_credentials():
    r = client.post('/api/connections', headers={'Origin': 'https://unrelated.example'}, json={'tavily': 'bad'})
    assert r.status_code == 403


def test_canonical_urls():
    assert canonical_url('https://example.com/news/?utm_source=x&id=3#section') == 'https://example.com/news?id=3'
    assert canonical_url('javascript:alert(1)') == ''
    assert canonical_url('https://user:password@example.com') == ''


def test_scripted_mode_is_rejected():
    response = client.post('/api/scan', json={'mode': 'demo', 'company': DEFAULT_COMPANY})
    assert response.status_code == 422
    assert '/api/demo' not in [r.path for r in app.routes]


def test_scan_uses_real_provider_path_by_default(monkeypatch):
    from backend import app as app_module
    monkeypatch.setenv('TAVILY_API_KEY', 'test')
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test')
    called = []
    async def collect(company, window):
        called.append(('search', window))
        return [{'id': 'source-from-api', 'title': 'Provider result', 'url': 'https://notion.so/update'}], [], []
    async def classify(item, company):
        called.append(('classify', item['id']))
        return {'verdict': 'Alert', 'provider': 'Jev', 'confidence': .95}
    monkeypatch.setattr(app_module, 'collect', collect)
    monkeypatch.setattr(app_module, 'classify', classify)
    response = client.post('/api/scan', json={'company': DEFAULT_COMPANY})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert called == [('search', 'day'), ('classify', 'source-from-api')]
    assert next(e['item']['id'] for e in events if e['type'] == 'source') == 'source-from-api'
    assert next(e['decision']['provider'] for e in events if e['type'] == 'decision') == 'Jev'
    assert events[-1]['type'] == 'complete' and events[-1]['count'] == 1


def test_search_failure_never_substitutes_results(monkeypatch):
    from backend import app as app_module
    from backend.providers import ProviderError
    monkeypatch.setenv('TAVILY_API_KEY', 'test')
    monkeypatch.setenv('TYPESAFE_API_KEY', 'test')
    async def collect(*args):
        raise ProviderError('Tavily unavailable')
    monkeypatch.setattr(app_module, 'collect', collect)
    response = client.post('/api/scan', json={'company': DEFAULT_COMPANY})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1] == {'type': 'error', 'message': 'Tavily unavailable'}
    assert not any(e['type'] in ('source', 'decision', 'complete') for e in events)


@pytest.mark.parametrize('domain_fields', [{}, {'domain': ''}, {'domain': None}])
def test_company_save_accepts_names_without_websites(monkeypatch, tmp_path, domain_fields):
    from backend import app as app_module
    monkeypatch.setattr(app_module, 'ROOT', tmp_path)
    company = {**DEFAULT_COMPANY, 'audience': '', 'competitors': [{'name': 'Linear', **domain_fields}]}
    response = client.put('/api/company', json=company)
    assert response.status_code == 200
    assert response.json()['competitors'] == [{'name': 'Linear', 'domain': ''}]
    assert json.loads((tmp_path / 'data/company.json').read_text())['competitors'][0]['domain'] == ''


def test_optional_website_still_validates_when_supplied():
    from backend.models import Competitor
    from pydantic import ValidationError
    assert Competitor(name='Linear', domain='https://linear.app/changelog').domain == 'linear.app'
    with pytest.raises(ValidationError):
        Competitor(name='Linear', domain='not a domain')


def test_simplified_company_brief_accepts_combined_context():
    company = Company(**{**DEFAULT_COMPANY, 'audience': '', 'description': 'Company and customer context. ' * 70,
        'priorities': [{'id': 'focus', 'label': 'What matters most', 'detail': 'Watch integrations; prioritize pricing. ' * 20, 'importance': 'high'}]})
    assert not company.audience
    assert len(company.description) > 1800
    assert len(company.priorities[0].detail) > 350
