import requests
from datetime import datetime
from zoneinfo import ZoneInfo

WEATHER_CODES = {
    "0": {
        "day": {"description": "Sunny"},
        "night": {"description": "Clear"}
    },
    "1": {
        "day": {"description": "Mainly Sunny"},
        "night": {"description": "Mainly Clear"}
    },
    "2": {
        "day": {"description": "Partly Cloudy"},
        "night": {"description": "Partly Cloudy"}
    },
    "3": {
        "day": {"description": "Cloudy"},
        "night": {"description": "Cloudy"}
    },
    "45": {
        "day": {"description": "Foggy"},
        "night": {"description": "Foggy"}
    },
    "48": {
        "day": {"description": "Rime Fog"},
        "night": {"description": "Rime Fog"}
    },
    "51": {
        "day": {"description": "Light Drizzle"},
        "night": {"description": "Light Drizzle"}
    },
    "53": {
        "day": {"description": "Drizzle"},
        "night": {"description": "Drizzle"}
    },
    "55": {
        "day": {"description": "Heavy Drizzle"},
        "night": {"description": "Heavy Drizzle"}
    },
    "56": {
        "day": {"description": "Light Freezing Drizzle"},
        "night": {"description": "Light Freezing Drizzle"}
    },
    "57": {
        "day": {"description": "Freezing Drizzle"},
        "night": {"description": "Freezing Drizzle"}
    },
    "61": {
        "day": {"description": "Light Rain"},
        "night": {"description": "Light Rain"}
    },
    "63": {
        "day": {"description": "Rain"},
        "night": {"description": "Rain"}
    },
    "65": {
        "day": {"description": "Heavy Rain"},
        "night": {"description": "Heavy Rain"}
    },
    "66": {
        "day": {"description": "Light Freezing Rain"},
        "night": {"description": "Light Freezing Rain"}
    },
    "67": {
        "day": {"description": "Freezing Rain"},
        "night": {"description": "Freezing Rain"}
    },
    "71": {
        "day": {"description": "Light Snow"},
        "night": {"description": "Light Snow"}
    },
    "73": {
        "day": {"description": "Snow"},
        "night": {"description": "Snow"}
    },
    "75": {
        "day": {"description": "Heavy Snow"},
        "night": {"description": "Heavy Snow"}
    },
    "77": {
        "day": {"description": "Snow Grains"},
        "night": {"description": "Snow Grains"}
    },
    "80": {
        "day": {"description": "Light Showers"},
        "night": {"description": "Light Showers"}
    },
    "81": {
        "day": {"description": "Showers"},
        "night": {"description": "Showers"}
    },
    "82": {
        "day": {"description": "Heavy Showers"},
        "night": {"description": "Heavy Showers"}
    },
    "85": {
        "day": {"description": "Light Snow Showers"},
        "night": {"description": "Light Snow Showers"}
    },
    "86": {
        "day": {"description": "Snow Showers"},
        "night": {"description": "Snow Showers"}
    },
    "95": {
        "day": {"description": "Thunderstorm"},
        "night": {"description": "Thunderstorm"}
    },
    "96": {
        "day": {"description": "Light Thunderstorms With Hail"},
        "night": {"description": "Light Thunderstorms With Hail"}
    },
    "99": {
        "day": {"description": "Thunderstorm With Hail"},
        "night": {"description": "Thunderstorm With Hail"}
    }
}

def get_weather_forecast(latitude, longitude):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}&"
        f"hourly=temperature_2m,weathercode&"
        f"daily=weathercode,temperature_2m_min,temperature_2m_max&"
        f"timezone=auto"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        timezone = data["timezone"]
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        today = now.date()
        hourly_filtered = {
            "time": [],
            "temperature_2m": [],
            "weather_description": []
        }
        daily_filtered = {
            "time": [],
            "temp_min": [],
            "temp_max": [],
            "weather_description": []
        }
        for i, time_str in enumerate(data["hourly"]["time"]):
            dt = datetime.fromisoformat(time_str)
            dt = dt.replace(tzinfo=tz)
            if dt.date() == today and dt > now:
                code = str(data["hourly"]["weathercode"][i])
                is_day = 6 <= dt.hour < 18
                period = "day" if is_day else "night"
                description = WEATHER_CODES.get(code, {}).get(period, {}).get("description", "Unknown")
                hourly_filtered["time"].append(time_str)
                hourly_filtered["temperature_2m"].append(data["hourly"]["temperature_2m"][i])
                hourly_filtered["weather_description"].append(description)
        for i, date_str in enumerate(data["daily"]["time"]):
            dt = datetime.fromisoformat(date_str).date()
            if dt > today:
                code = str(data["daily"]["weathercode"][i])
                description = WEATHER_CODES.get(code, {}).get("day", {}).get("description", "Unknown")

                daily_filtered["time"].append(date_str)
                daily_filtered["temp_max"].append(data["daily"]["temperature_2m_max"][i])
                daily_filtered["temp_min"].append(data["daily"]["temperature_2m_min"][i])
                daily_filtered["weather_description"].append(description)
        return {
            "timezone": data["timezone"],
            "hourly": hourly_filtered,
            "daily": daily_filtered
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None