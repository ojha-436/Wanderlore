import httpx
import logging

logger = logging.getLogger(__name__)

async def get_weather_advisory(destination: str) -> dict:
    """
    Fetches coordinates for the destination, then fetches weather/climate data
    from the free Open-Meteo API.
    """
    try:
        # 1. Geocode the destination to get Lat/Lng
        async with httpx.AsyncClient() as client:
            geo_res = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": destination, "count": 1, "format": "json"}
            )
            geo_res.raise_for_status()
            geo_data = geo_res.json()
            
            if "results" not in geo_data or len(geo_data["results"]) == 0:
                logger.warning(f"Geocoding failed for {destination}")
                return {"error": "Location not found"}
                
            location = geo_data["results"][0]
            lat = location["latitude"]
            lon = location["longitude"]
            
            # 2. Fetch 7-day weather forecast
            weather_res = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                    "timezone": "auto",
                    "forecast_days": 7
                }
            )
            weather_res.raise_for_status()
            weather_data = weather_res.json()
            
            daily = weather_data.get("daily", {})
            if not daily:
                return {"error": "Weather data unavailable"}
                
            # Aggregate to create an advisory
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            precip = daily.get("precipitation_probability_max", [])
            
            avg_high = sum(max_temps) / len(max_temps) if max_temps else 0
            avg_low = sum(min_temps) / len(min_temps) if min_temps else 0
            max_precip = max(precip) if precip else 0
            
            return {
                "avg_high_c": round(avg_high, 1),
                "avg_low_c": round(avg_low, 1),
                "rain_chance_pct": max_precip,
                "summary": f"Expect highs around {round(avg_high)}°C and lows of {round(avg_low)}°C over the next week. Maximum rain probability is {max_precip}%."
            }
    except Exception as e:
        logger.error(f"Error fetching weather for {destination}: {e}")
        return {"error": "Failed to fetch weather data"}
