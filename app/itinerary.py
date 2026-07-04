"""Deterministic itinerary day-packing.

This is intentionally NOT done by the LLM. Gemini suggests places and durations;
this pure function packs the traveler's chosen items into days within a daily time
budget, and surfaces anything that doesn't fit as `overflow` (never silently
dropped). Correct, explainable, and unit-tested.
"""
from typing import List

from .schemas import Itinerary, ItineraryDay, ItineraryItem, ItineraryItemInput


def pack_itinerary(
    items: List[ItineraryItemInput], num_days: int, daily_minutes: int
) -> Itinerary:
    """Greedy first-fit-decreasing packing across `num_days`.

    Larger items are placed first (better packing). Anything that cannot fit in any
    day within `daily_minutes` goes to `overflow`.
    """
    if num_days < 1:
        raise ValueError("num_days must be >= 1")
    if daily_minutes < 1:
        raise ValueError("daily_minutes must be >= 1")

    day_items: List[List[ItineraryItem]] = [[] for _ in range(num_days)]
    used = [0] * num_days
    overflow: List[ItineraryItem] = []

    # First-fit decreasing: sort by duration desc (stable → preserves input order on ties).
    ordered = sorted(
        enumerate(items), key=lambda pair: pair[1].duration_minutes, reverse=True
    )

    for _, raw in ordered:
        item = ItineraryItem(
            id=raw.id, name=raw.name, category=raw.category, duration_minutes=raw.duration_minutes
        )
        placed = False
        for d in range(num_days):
            if used[d] + item.duration_minutes <= daily_minutes:
                day_items[d].append(item)
                used[d] += item.duration_minutes
                placed = True
                break
        if not placed:
            overflow.append(item)

    days = [
        ItineraryDay(day_number=d + 1, items=day_items[d], minutes_used=used[d])
        for d in range(num_days)
    ]
    return Itinerary(
        days=days,
        overflow=overflow,
        daily_minutes_budget=daily_minutes,
        total_minutes_planned=sum(used),
    )
