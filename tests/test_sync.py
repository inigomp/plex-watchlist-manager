"""Tests de la lógica incremental de sync (modo, merge y construcción de items).

TMDB se mockea para no salir a la red; Mongo no se toca (las funciones probadas
son puras respecto al estado que reciben por parámetro).
"""
import time

import pytest

import sync
from sync import _should_run_full, _merge_libs, _build_item

WL_ITEM = {
    "ratingKey": "A",
    "title": "Peli A",
    "originalTitle": "Peli A",
    "year": 2020,
    "type": "movie",
    "guid": None,
    "thumb": None,
}


class TestShouldRunFull:
    def test_forced(self):
        assert _should_run_full({"last_success_timestamp": 1, "last_full_timestamp": 1}, True) is True

    def test_first_ever_sync(self):
        assert _should_run_full({}, False) is True

    def test_missing_full_timestamp(self):
        assert _should_run_full({"last_success_timestamp": 1}, False) is True

    def test_recent_full_stays_incremental(self):
        now = int(time.time())
        status = {"last_success_timestamp": now, "last_full_timestamp": now}
        assert _should_run_full(status, False) is False

    def test_stale_full_escalates(self):
        now = int(time.time())
        status = {"last_success_timestamp": now, "last_full_timestamp": now - 8 * 86400}
        assert _should_run_full(status, False) is True


class TestMergeLibs:
    def test_dedup_and_append(self):
        assert _merge_libs(["Cine"], ["Cine", "4K"]) == ["Cine", "4K"]

    def test_empty_old(self):
        assert _merge_libs([], ["4K"]) == ["4K"]

    def test_preserves_order(self):
        assert _merge_libs(["A", "B"], ["C"]) == ["A", "B", "C"]


class TestBuildItemIncremental:
    def test_preserves_availability_without_new_match(self, monkeypatch):
        monkeypatch.setattr(sync, "get_score", lambda *a: pytest.fail("no debería consultar TMDB"))
        old = {"A": {"plex_id": "A", "on_server": True, "libraries": ["Cine"],
                     "score": "6.0", "owners": ["Rebe"], "added_at": 100}}
        item = _build_item(WL_ITEM, 0, [], old, incremental=True)
        assert item["on_server"] is True
        assert item["libraries"] == ["Cine"]
        assert item["score"] == "6.0"
        assert item["owners"] == ["Rebe"]

    def test_upgrades_availability_on_new_match(self, monkeypatch):
        monkeypatch.setattr(sync, "get_score", lambda *a: pytest.fail("no debería consultar TMDB"))
        old = {"A": {"plex_id": "A", "on_server": False, "libraries": [],
                     "score": "7.5", "owners": [], "added_at": 0}}
        srv = [{"title": "peli a", "orig": "peli a", "year": 2020,
                "guid": None, "lib": "Estrenos", "added_at": 999}]
        item = _build_item(WL_ITEM, 0, srv, old, incremental=True)
        assert item["on_server"] is True
        assert item["libraries"] == ["Estrenos"]
        assert item["score"] == "7.5"  # reutilizado, no re-consultado

    def test_new_watchlist_item_queries_tmdb(self, monkeypatch):
        calls = []
        monkeypatch.setattr(sync, "get_score", lambda *a: calls.append(a) or "9.9")
        item = _build_item(WL_ITEM, 0, [], {}, incremental=True)  # old_docs vacío -> item nuevo
        assert len(calls) == 1
        assert item["score"] == "9.9"
        assert item["on_server"] is False


class TestBuildItemFull:
    def test_recomputes_from_scratch(self, monkeypatch):
        monkeypatch.setattr(sync, "get_score", lambda *a: "5.5")
        # El estado previo decía on_server=True, pero en modo completo se ignora.
        old = {"A": {"plex_id": "A", "on_server": True, "libraries": ["Cine"],
                     "score": "1.0", "owners": ["Rebe"]}}
        item = _build_item(WL_ITEM, 0, [], old, incremental=False)
        assert item["on_server"] is False  # sin match en servidor -> recalculado a False
        assert item["libraries"] == []
        assert item["score"] == "5.5"  # siempre se consulta en completo
        assert item["owners"] == ["Rebe"]  # owners siempre se preservan
