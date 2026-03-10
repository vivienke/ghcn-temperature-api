import pytest
from datetime import date
from fastapi import HTTPException
from typing import cast
from fastapi import Request
from app.api.validation import validate_years_or_raise_http_400


class _DummyMetadataStore:
    def __init__(self, min_year: int):
        self._min_year = min_year

    def ui_min_year(self):
        return self._min_year


class _DummyAppState:
    def __init__(self, min_year: int):
        self.metadata_store = _DummyMetadataStore(min_year)


class _DummyApp:
    def __init__(self, min_year: int):
        self.state = _DummyAppState(min_year)


class _DummyRequest:
    def __init__(self, min_year: int):
        self.app = _DummyApp(min_year)


@pytest.mark.asyncio
async def test_validate_years_or_raise_http_400_ok():
    req = _DummyRequest(min_year=1800)
    end_ok = date.today().year - 1  # max_year ist intern: currentYear - 1
    await validate_years_or_raise_http_400(cast(Request, req), start_year=2000, end_year=end_ok)


@pytest.mark.asyncio
async def test_validate_years_or_raise_http_400_converts_to_http_400():
    req = _DummyRequest(min_year=1800)
    end_too_big = date.today().year  # 1 höher als erlaubt
    with pytest.raises(HTTPException) as exc:
        await validate_years_or_raise_http_400(cast(Request, req), start_year=2000, end_year=end_too_big)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_validate_years_or_raise_http_400_start_after_end_400():
    req = _DummyRequest(min_year=1800)
    with pytest.raises(HTTPException) as exc:
        await validate_years_or_raise_http_400(cast(Request, req), start_year=2010, end_year=2000)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_validate_years_or_raise_http_400_start_below_min_400():
    req = _DummyRequest(min_year=1900)
    with pytest.raises(HTTPException) as exc:
        await validate_years_or_raise_http_400(cast(Request, req), start_year=1800, end_year=2000)
    assert exc.value.status_code == 400