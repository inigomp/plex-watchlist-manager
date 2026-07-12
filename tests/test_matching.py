"""Tests del cruce watchlist <-> servidor (función pura, sin dependencias)."""
from matching import find_availability


def server_item(**kw):
    base = {"title": "", "orig": "", "year": 0, "guid": None, "lib": "Cine", "added_at": 0}
    base.update(kw)
    return base


class TestGuidMatch:
    def test_match_by_rating_key_suffix(self):
        srv = [server_item(guid="plex://movie/abc123", added_at=50)]
        assert find_availability("abc123", None, "X", None, 2020, srv) == (True, ["Cine"], 50)

    def test_match_by_exact_guid(self):
        srv = [server_item(guid="plex://movie/xyz", added_at=10)]
        on, libs, added = find_availability("zzz", "plex://movie/xyz", "X", None, 2020, srv)
        assert on is True and libs == ["Cine"] and added == 10

    def test_guid_wins_and_stops_early(self):
        srv = [
            server_item(guid="plex://m/1", lib="Cine", added_at=99),
            server_item(title="x", year=2020, lib="4K", added_at=5),
        ]
        # El match por GUID corta el bucle: solo coge la primera librería.
        assert find_availability("1", None, "X", None, 2020, srv) == (True, ["Cine"], 99)


class TestTitleYearMatch:
    def test_within_tolerance(self):
        srv = [server_item(title="anaconda", year=1997)]
        on, _, _ = find_availability("zzz", None, "Anaconda", None, 1996, srv)
        assert on is True

    def test_outside_tolerance(self):
        srv = [server_item(title="anaconda", year=1997)]
        on, _, _ = find_availability("zzz", None, "Anaconda", None, 1990, srv)
        assert on is False

    def test_original_title_match(self):
        srv = [server_item(title="the dinner", orig="the dinner", year=2017)]
        on, _, _ = find_availability("zzz", None, "La cena", "The Dinner", 2017, srv)
        assert on is True

    def test_cross_title_vs_orig(self):
        # El título del servidor coincide con el título original de la watchlist.
        srv = [server_item(title="the dinner", year=2017)]
        on, _, _ = find_availability("zzz", None, "La cena", "The Dinner", 2017, srv)
        assert on is True

    def test_accumulates_multiple_libraries(self):
        srv = [
            server_item(title="dune", year=2021, lib="Cine", added_at=10),
            server_item(title="dune", year=2021, lib="4K", added_at=20),
        ]
        on, libs, _ = find_availability("zzz", None, "Dune", None, 2021, srv)
        assert on is True and set(libs) == {"Cine", "4K"}


class TestNoMatch:
    def test_returns_defaults(self):
        srv = [server_item(title="other", year=2000)]
        assert find_availability("zzz", None, "X", None, 2020, srv) == (False, [], 0)

    def test_year_none_does_not_crash(self):
        # Regresión: antes 'None > 0' lanzaba TypeError.
        srv = [server_item(title="anaconda", year=1997)]
        assert find_availability("zzz", None, "Anaconda", None, None, srv) == (False, [], 0)

    def test_no_fallback_when_server_year_is_zero(self):
        srv = [server_item(title="anaconda", year=0)]
        on, _, _ = find_availability("zzz", None, "Anaconda", None, 1997, srv)
        assert on is False

    def test_empty_server(self):
        assert find_availability("zzz", "plex://x", "X", "X", 2020, []) == (False, [], 0)
