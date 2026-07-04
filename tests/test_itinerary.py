"""Deterministic itinerary packer — pure unit tests, no mocks (the crown jewel)."""
import pytest

from app.itinerary import pack_itinerary

from .factories import items


def test_items_fit_within_budget():
    it = pack_itinerary(items(120, 90, 60), num_days=1, daily_minutes=300)
    assert len(it.days) == 1
    assert len(it.days[0].items) == 3
    assert it.days[0].minutes_used == 270
    assert it.overflow == []


def test_overflow_when_over_capacity():
    # 3 x 200 min into 1 day of 300 min → one fits, two overflow.
    it = pack_itinerary(items(200, 200, 200), num_days=1, daily_minutes=300)
    assert len(it.days[0].items) == 1
    assert len(it.overflow) == 2


def test_spreads_across_days():
    it = pack_itinerary(items(180, 180, 180), num_days=3, daily_minutes=200)
    # each 180 fits once per 200-min day → one per day, no overflow
    assert [len(d.items) for d in it.days] == [1, 1, 1]
    assert it.overflow == []


def test_minutes_used_never_exceeds_budget():
    it = pack_itinerary(items(90, 90, 90, 90, 90), num_days=2, daily_minutes=200)
    for d in it.days:
        assert d.minutes_used <= 200


def test_first_fit_decreasing_places_biggest_first():
    it = pack_itinerary(items(30, 240, 30), num_days=1, daily_minutes=250)
    # 240 placed first (fits), then only room for none more (240+30>250) → two overflow
    assert it.days[0].items[0].duration_minutes == 240
    assert len(it.overflow) == 2


def test_empty_items():
    it = pack_itinerary([], num_days=2, daily_minutes=300)
    assert it.total_minutes_planned == 0
    assert all(len(d.items) == 0 for d in it.days)


def test_zero_days_raises():
    with pytest.raises(ValueError):
        pack_itinerary(items(60), num_days=0, daily_minutes=300)


def test_zero_budget_raises():
    with pytest.raises(ValueError):
        pack_itinerary(items(60), num_days=1, daily_minutes=0)


def test_day_numbers_are_sequential():
    it = pack_itinerary(items(60), num_days=3, daily_minutes=120)
    assert [d.day_number for d in it.days] == [1, 2, 3]
