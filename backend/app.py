import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .defaults import DEFAULT_COMPANY
from .models import Company, Credentials, ScanRequest
from .providers import ProviderError, classify, collect, keys, require_keys

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
app = FastAPI(title='Signal Desk', version='1.0.0')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])


@app.middleware('http')
async def local_requests(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and origin not in ('http://localhost:8765', 'http://127.0.0.1:8765', 'http://localhost:5173', 'http://127.0.0.1:5173'):
            return JSONResponse({'detail': 'Only the local app may write to this server.'}, status_code=403)
        if 'application/json' not in request.headers.get('content-type', ''):
            return JSONResponse({'detail': 'JSON body required.'}, status_code=415)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.exception_handler(ProviderError)
async def provider_error(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=503)


def read_company():
    try:
        return Company.model_validate_json((ROOT / 'data/company.json').read_text()).model_dump()
    except (OSError, ValueError):
        return deepcopy(DEFAULT_COMPANY)


@app.get('/api/config')
def config():
    tavily, jev = keys()
    return {'company': read_company(), 'connected': {'tavily': bool(tavily), 'jev': bool(jev)}}


@app.put('/api/company')
def save_company(company: Company):
    folder = ROOT / 'data'
    folder.mkdir(exist_ok=True)
    temp = folder / 'company.tmp'
    temp.write_text(company.model_dump_json(indent=2))
    temp.replace(folder / 'company.json')
    return company.model_dump()


@app.post('/api/connections')
def connect(credentials: Credentials):
    # Keys live in server memory only; never in localStorage, responses, or logs.
    if credentials.tavily.strip():
        os.environ['TAVILY_API_KEY'] = credentials.tavily.strip()
    if credentials.jev.strip():
        os.environ['TYPESAFE_API_KEY'] = credentials.jev.strip()
    return {'tavily': bool(keys()[0]), 'jev': bool(keys()[1])}


def event(kind, **data):
    return json.dumps({'type': kind, **data}, ensure_ascii=False) + '\n'


@app.post('/api/scan')
async def scan(body: ScanRequest):
    require_keys()
    async def stream():
        yield event('stage', message='Tavily is searching the watchlist…')
        try:
            items, warnings, traces = await collect(body.company, body.window)
            for message in warnings:
                yield event('warning', message=message)
            yield event('trace', traces=traces)
            for item in items:
                yield event('source', item=item)
            yield event('stage', message=f'jev is evaluating {len(items)} sources against your priorities…')
            semaphore = asyncio.Semaphore(4)
            async def judge(item):
                async with semaphore:
                    try:
                        return item['id'], await classify(item, body.company), None
                    except ProviderError as exc:
                        return item['id'], None, str(exc)
            tasks = [asyncio.create_task(judge(item)) for item in items]
            failed = 0
            try:
                for future in asyncio.as_completed(tasks):
                    ident, decision, error = await future
                    if error:
                        failed += 1
                        yield event('source_error', id=ident, message=error)
                    else:
                        yield event('decision', id=ident, decision=decision)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
            if failed:
                yield event('warning', message=f'jev could not evaluate {failed} source(s). These items have no decision. Check your jev key or quota and retry.')
            yield event('complete', count=len(items), failed=failed, completed_at=datetime.now(timezone.utc).isoformat())
        except ProviderError as exc:
            yield event('error', message=str(exc))
        except Exception:
            yield event('error', message='The scan could not finish. Please retry.')
    return StreamingResponse(stream(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})



if (ROOT / 'frontend/dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'frontend/dist', html=True), name='frontend')
