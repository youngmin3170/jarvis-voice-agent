import requests
from utils import get_geocoding, get_default_location_name

def get_current_weather(location: str = None) -> str:
    """
    Fetches current real-time weather conditions.
    If location is None or not specified, auto-detects the user's location.
    
    Args:
        location: City or region name (optional). Leave empty/None for current user location.
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Fetching current weather...")
    try:
        lat, lon, city, country = get_geocoding(location)
        
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m"
            f"&models=best_match"
        )
        weather_res = requests.get(weather_url, timeout=5).json()
        
        if "current" in weather_res:
            curr = weather_res["current"]
            temp = curr["temperature_2m"]
            feels_like = curr["apparent_temperature"]
            precip = curr["precipitation"]
            wind = curr["wind_speed_10m"]
            
            return (
                f"Current Weather in {city}, {country}:\n"
                f"- Temperature: {temp}°C (Feels like {feels_like}°C)\n"
                f"- Current Precipitation: {precip} mm\n"
                f"- Wind Speed: {wind} km/h"
            )
        raise Exception("Invalid weather response payload.")
        
    except Exception as e:
        print(f"[System Warning]: Primary weather fetch failed ({e}). Executing wttr.in fallback...")
        target_loc = location if location else get_default_location_name()
        return _wttr_fallback(target_loc, is_forecast=False)


def get_weather_forecast(location: str = None, days: int = 7) -> str:
    """
    Fetches multi-day forecast (highs/lows, rain probability, UV index).
    If location is None, auto-detects the user's location. Use this for questions like 
    'Should I take an umbrella today/tomorrow?' or planning gear/clothing for the day.   
     
    Args:
        location: City or region name (optional). Leave empty/None for current user location.
        days: Number of days to forecast (default 7, max 16).
    """
    print(f"\n[J.A.R.V.I.S. Internal]: Fetching forecast...")
    
    requested_days = days
    days = max(1, min(days, 16))

    try:
        lat, lon, city, country = get_geocoding(location)
        
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
            f"precipitation_sum,precipitation_probability_max,uv_index_max"
            f"&timezone=auto&forecast_days={days}&models=best_match"
        )
        forecast_res = requests.get(forecast_url, timeout=5).json()
        
        if "daily" in forecast_res:
            daily = forecast_res["daily"]
            dates = daily["time"]
            max_temps = daily["temperature_2m_max"]
            min_temps = daily["temperature_2m_min"]
            feels_max = daily["apparent_temperature_max"]
            precip_sum = daily["precipitation_sum"]
            precip_prob = daily["precipitation_probability_max"]
            uv_max = daily["uv_index_max"]
            
            header_note = f" (capped at API max of 16 days)" if requested_days > 16 else ""
            lines = [f"{days}-Day Forecast for {city}, {country}{header_note}:"]
            
            for i in range(len(dates)):
                lines.append(
                    f"- {dates[i]}: High {max_temps[i]}°C (Feels like {feels_max[i]}°C), Low {min_temps[i]}°C | "
                    f"Rain Prob: {precip_prob[i]}% ({precip_sum[i]}mm) | Max UV Index: {uv_max[i]}"
                )
            return "\n".join(lines)
            
        raise Exception("Invalid forecast response payload.")
        
    except Exception as e:
        print(f"[System Warning]: Primary forecast fetch failed ({e}). Executing wttr.in fallback...")
        target_loc = location if location else get_default_location_name()
        return _wttr_fallback(target_loc, is_forecast=True)


def _wttr_fallback(location: str, is_forecast: bool = False) -> str:
    """Helper fallback handler for wttr.in."""
    try:
        if is_forecast:
            res = requests.get(f"https://wttr.in/{location}?3&T", timeout=5)
            if res.status_code == 200:
                clean_text = "\n".join([line for line in res.text.split('\n') if line.strip()][:12])
                return f"Fallback Forecast for {location}:\n{clean_text}"
        else:
            res = requests.get(f"https://wttr.in/{location}?format=%C+%t", timeout=5)
            if res.status_code == 200:
                return f"Fallback Current Weather for {location}: {res.text.strip()}"
                
        return f"Unable to retrieve weather data for {location}."
    except Exception as e:
        return f"Error executing wttr.in fallback: {e}"