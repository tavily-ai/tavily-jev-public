from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class Priority(BaseModel):
    id: str = Field(min_length=1, max_length=40, pattern=r'^[a-zA-Z0-9_-]+$')
    label: str = Field(min_length=1, max_length=100)
    detail: str = Field(min_length=1, max_length=1800)
    importance: Literal['high', 'watch', 'off'] = 'high'


class Competitor(BaseModel):
    name: str = Field(min_length=1, max_length=70)
    domain: str = Field(default='', max_length=150)

    @field_validator('domain', mode='before')
    @classmethod
    def domain_only(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return ''
        if not isinstance(value, str):
            return value
        value = value.strip().lower()
        if '://' in value:
            value = urlparse(value).netloc
        if not value or any(c in value for c in '/:@ ?#') or '.' not in value:
            raise ValueError('Use a public domain such as notion.so')
        return value


class Company(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2200)
    audience: str = Field(default='', max_length=400)
    priorities: list[Priority] = Field(min_length=1, max_length=6)
    competitors: list[Competitor] = Field(min_length=1, max_length=5)

    @field_validator('priorities')
    @classmethod
    def unique_ids(cls, value):
        if len({p.id for p in value}) != len(value) or any(p.id == 'none' for p in value):
            raise ValueError('Priority IDs must be unique; none is reserved')
        return value


class ScanRequest(BaseModel):
    mode: Literal['live'] = 'live'
    window: Literal['day', 'week', 'month'] = 'day'
    company: Company


class Credentials(BaseModel):
    tavily: str = Field(default='', max_length=500)
    jev: str = Field(default='', max_length=500)
