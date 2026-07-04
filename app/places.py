import httpx
import logging
import asyncio
from typing import Optional, List, Dict, Any
from app.config import get_settings

logger = logging.getLogger(__name__)

async def enrich_place_with_google(name: str, destination: str) -> dict:
    """
    Queries Google Places API (New) via Text Search to find the place and fetch
    its photo and rating.
    """
    settings = get_settings()
    api_key = settings.google_maps_api_key
    if not api_key:
        return {"photo_url": None, "rating": None}
        
    query = f"{name} in {destination}"
    url = "https://places.googleapis.com/v1/places:searchText"
    
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.rating,places.photos",
        "Content-Type": "application/json"
    }
    
    payload = {
        "textQuery": query,
        "languageCode": "en",
        "maxResultCount": 1
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=headers, json=payload, timeout=5.0)
            res.raise_for_status()
            data = res.json()
            
            places = data.get("places", [])
            if not places:
                return {"photo_url": None, "rating": None}
                
            place = places[0]
            rating = place.get("rating")
            
            photo_url = None
            photos = place.get("photos", [])
            if photos:
                photo_name = photos[0].get("name")
                if photo_name:
                    # Construct the photo URL
                    photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&maxWidthPx=400&key={api_key}"
            
            return {"photo_url": photo_url, "rating": rating}
    except Exception as e:
        logger.error(f"Error enriching place '{query}': {e}")
        return {"photo_url": None, "rating": None}

async def enrich_items(items: list, destination: str):
    """Enriches a list of Attraction or HiddenGem objects in place."""
    async def _enrich(item):
        enrichment = await enrich_place_with_google(item.name, destination)
        item.photo_url = enrichment["photo_url"]
        item.rating = enrichment["rating"]
        
    await asyncio.gather(*[_enrich(item) for item in items])
