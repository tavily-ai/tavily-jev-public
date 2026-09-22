"""Tavily retrieves evidence; Jev makes finite, typed decisions about it."""
import asyncio
import hashlib
import json
import os
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from tavily import AsyncTavilyClient

from .models import Company

class ProviderError(Exception):
    pass


def keys():
    return os.getenv('TAVILY_API_KEY', ''), os.getenv('TYPESAFE_API_KEY', '') or os.getenv('JEV_API_KEY', '')


def require_keys():
    tavily, jev = keys()
    missing = [name for name, value in [('Tavily', tavily), ('jev', jev)] if not value]
    if missing:
        raise ProviderError('Connect ' + ' and '.join(missing) + ' in Connections to run live.')


def canonical_url(url: str):
    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username:
        return ''
    query = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if not k.startswith('utm_') and k not in ('fbclid', 'gclid')])
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip('/'), query, ''))


def choice(instructions, criteria):
    return {'type': 'choice', 'instructions': instructions, 'criteria': criteria}


async def evaluate(state, questions):
    """Official Jev HTTP contract, with bounded retries and validated responses."""
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=35) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    'https://api.typesafe.ai/v1/systemone',
                    headers={'Authorization': f'Bearer {keys()[1]}'},
                    json={'model': os.getenv('JEV_MODEL', 'jev-latest'), 'state': state, 'questions': questions},
                )
            except httpx.HTTPError:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise ProviderError('jev could not be reached. Check your connection and retry.') from None
            if response.status_code in (429, 500, 502, 503, 529) and attempt < 2:
                try:
                    delay = min(float(response.headers.get('retry-after', 2 ** attempt)), 15)
                except ValueError:
                    delay = 2 ** attempt
                await asyncio.sleep(max(0, delay))
                continue
            if response.status_code != 200:
                raise ProviderError(f'jev returned HTTP {response.status_code}. Check your key or quota in Connections.')
            try:
                data = response.json()
                for name, question in questions.items():
                    answer = data['answers'][name]
                    allowed = question['criteria']
                    if answer['type'] != 'choice' or answer['choice'] not in allowed:
                        raise ValueError('Unexpected choice')
                    if not 0 <= float(answer['confidence']) <= 1:
                        raise ValueError('Invalid confidence')
                    probs = answer['probabilities']
                    if set(probs) != set(allowed) or any(not 0 <= float(p) <= 1 for p in probs.values()):
                        raise ValueError('Invalid probabilities')
                    if abs(sum(probs.values()) - 1) > .03:
                        raise ValueError('Probabilities do not sum to one')
                return data, round((time.monotonic() - started) * 1000)
            except (KeyError, ValueError, TypeError):
                raise ProviderError('jev returned an unexpected response shape. No decision was applied.') from None


_cache = {}


async def search(query, **kwargs):
    # Explicit depth and bounds prevent surprise auto-parameter cost increases.
    cache_key = hashlib.sha256(json.dumps([keys()[0], query, kwargs], sort_keys=True).encode()).hexdigest()
    if cache_key in _cache and time.monotonic() - _cache[cache_key][0] < 600:
        return {**_cache[cache_key][1], 'cached': True}
    client = AsyncTavilyClient(api_key=keys()[0], client_name='jev-tavily-signal-desk')
    try:
        for attempt in range(3):
            try:
                result = await client.search(
                    query=query[:390], search_depth='advanced', max_results=4,
                    include_answer=False, include_raw_content=False,
                    chunks_per_source=3, timeout=30, **kwargs,
                )
                if len(_cache) >= 128:
                    _cache.pop(next(iter(_cache)))
                _cache[cache_key] = (time.monotonic(), result)
                return {**result, 'cached': False}
            except Exception as exc:
                name = type(exc).__name__
                if any(s in name.lower() for s in ('timeout', 'ratelimit', 'connection')) and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise ProviderError('Tavily search failed. Check the API key, quota, and network connection.') from None
    finally:
        await client.close()


async def collect(company: Company, window):
    semaphore = asyncio.Semaphore(3)
    async def run(competitor, kind):
        async with semaphore:
            if kind == 'updates':
                query = f'{competitor.name} product launches pricing changes new features integrations announcements'
                result = await search(query, topic='news', time_range=window)
            else:
                query = f'{competitor.name} team plan pricing AI features'
                options = {'include_domains': [competitor.domain]} if competitor.domain else {}
                result = await search(query, topic='general', **options)
            return competitor, kind, query, result
    jobs = [run(c, kind) for c in company.competitors for kind in ('updates', 'baseline')]
    results = await asyncio.gather(*jobs, return_exceptions=True)
    items, seen, warnings, traces = [], set(), [], []
    for result in results:
        if isinstance(result, Exception):
            warnings.append(str(result) if isinstance(result, ProviderError) else 'A search could not complete.')
            continue
        competitor, kind, query, response = result
        traces.append({'provider': 'Tavily', 'query': query, 'request_id': response.get('request_id'), 'cached': response['cached']})
        for r in response.get('results', []):
            url = canonical_url(r.get('url', ''))
            if not url or url in seen or not r.get('content'):
                continue
            seen.add(url)
            domain = urlsplit(url).netloc.removeprefix('www.')
            items.append({
                'id': hashlib.sha256(url.encode()).hexdigest()[:12],
                'competitor': competitor.name, 'domain': domain, 'url': url,
                'title': r.get('title', 'Untitled source'), 'content': r['content'][:7000],
                'kind': 'Current snapshot' if kind == 'baseline' else 'Recent coverage',
                'baseline': kind == 'baseline', 'published_date': r.get('published_date') or 'Publication date unavailable',
                'source_type': 'Official source' if competitor.domain and (domain == competitor.domain or domain.endswith('.' + competitor.domain)) else 'Web coverage',
                'retrieval_score': r.get('score'), 'synthetic': False,
            })
    if not traces:
        raise ProviderError(warnings[0] if warnings else 'Tavily returned no search responses.')
    return items[:18], list(dict.fromkeys(warnings)), traces


async def classify(item, company):
    source = {key: item[key] for key in ('title', 'content', 'url', 'published_date') if key in item}
    data, latency = await evaluate(
        {'company': company.model_dump(), 'source': source},
        {'triage': choice('How important is this source for this company?', {
            'Alert': None, 'Watch': None, 'Ignore': None,
        })},
    )
    answer = data['answers']['triage']
    return {
        'verdict': answer['choice'],
        'confidence': answer['confidence'], 'probabilities': answer['probabilities'],
        'model': data['model'], 'latency_ms': latency,
        'provider': 'Jev', 'usage': data.get('usage', {}),
    }
