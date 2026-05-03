import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from olvid import OlvidClient, datatypes, tools
from fetch import get_weather_forecast
from zoneinfo import ZoneInfo
from datetime import datetime

WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]

WEATHER_EMOJIS = {
    "Sunny": "☀️",
    "Mainly Sunny": "🌤",
    "Partly Cloudy": "⛅",
    "Cloudy": "☁️",
    "Foggy": "🌫",
    "Rime Fog": "🌫",
    "Light Drizzle": "🌦",
    "Drizzle": "🌦",
    "Heavy Drizzle": "🌧",
    "Light Freezing Drizzle": "🌧",
    "Freezing Drizzle": "🌧",
    "Light Rain": "🌦",
    "Rain": "🌧",
    "Heavy Rain": "🌧",
    "Light Freezing Rain": "🌧",
    "Freezing Rain": "🌧",
    "Light Snow": "🌨",
    "Snow": "❄️",
    "Heavy Snow": "❄️",
    "Snow Grains": "❄️",
    "Light Showers": "🌦",
    "Showers": "🌦",
    "Heavy Showers": "🌧",
    "Light Snow Showers": "🌨",
    "Snow Showers": "🌨",
    "Thunderstorm": "⛈",
    "Light Thunderstorms With Hail": "⛈",
    "Thunderstorm With Hail": "⛈",
    "Clear": "💫",
    "Mainly Clear": "💫"
}

class Evelyne(OlvidClient):
    def __init__(self):
        super().__init__()
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

    async def restore_data(self):
        await self.restore_scheduled_time_for_discussions()

    async def store_location_for_discussion(self, discussion_id: int, latitude: float, longitude: float):
        location_str = f"{latitude},{longitude}"
        await self.discussion_storage_set(discussion_id, "location", location_str)

    async def get_location_for_discussion(self, discussion_id: int):
        location_str = await self.discussion_storage_get(discussion_id, "location")
        if location_str:
            latitude, longitude = map(float, location_str.split(","))
            return latitude, longitude
        return None, None

    async def store_scheduled_time_for_discussion(self, discussion_id: int, time_str: str):
        await self.discussion_storage_set(discussion_id, "scheduled_time", time_str)

    async def get_scheduled_time_for_discussion(self, discussion_id: int):
        return await self.discussion_storage_get(discussion_id, "scheduled_time")

    async def restore_scheduled_time_for_discussions(self):
        discussions_generator = self.discussion_list()
        async for discussion in discussions_generator:
            scheduled_time = await self.get_scheduled_time_for_discussion(discussion.id)
            if scheduled_time:
                try:
                    hour, minute = map(int, scheduled_time.split(":"))
                    self.scheduler.add_job(
                        self.send_weather_alert,
                        CronTrigger(hour=hour, minute=minute, timezone="UTC"),
                        args=[discussion.id],
                        id=f"weather_alert_{discussion.id}",
                        replace_existing=True
                    )
                except ValueError:
                    print(f"Invalid time format for discussion {discussion.id}: {scheduled_time}")

    def format_forecast(self, forecast, tz):
        today_summary = forecast.get("today_summary", {})
        temp_min = today_summary.get("temp_min", "?")
        temp_max = today_summary.get("temp_max", "?")
        weather_desc = today_summary.get("weather_description", "")
        emoji_today = WEATHER_EMOJIS.get(weather_desc, "🌡")

        response = f"🌤 Hello! Here is your weather forecast 🌤\n\n"

        # Résumé du jour
        response += f"📋 Today's summary: {emoji_today} {weather_desc}, {temp_min}°C / {temp_max}°C\n\n"

        # Détails matin / midi / soir
        SLOT_LABELS = {"08:00": "🌅 Morning (8h)", "14:00": "☀️ Afternoon (14h)", "20:00": "🌆 Evening (20h)"}
        slots = {label: None for label in SLOT_LABELS}

        for i, time_str in enumerate(forecast["hourly"]["time"]):
            dt = datetime.fromisoformat(time_str)
            hour = dt.strftime("%H:%M")
            if hour in SLOT_LABELS:
                temp = forecast["hourly"]["temperature_2m"][i]
                weather = forecast["hourly"]["weather_description"][i]
                emoji = WEATHER_EMOJIS.get(weather, "🌡")
                slots[hour] = f"{emoji} {temp}°C, {weather}"

        response += "🕒 Details:\n"
        for hour_key, label in SLOT_LABELS.items():
            value = slots.get(hour_key) or "N/A"
            response += f"  {label}: {value}\n"

        # Jours suivants
        response += "\n📅 Next days:\n"
        today = datetime.now(tz).date()
        for i, date_str in enumerate(forecast["daily"]["time"]):
            date_obj = datetime.fromisoformat(date_str).date()
            delta = (date_obj - today).days
            label = "Tomorrow" if delta == 1 else WEEKDAYS[date_obj.weekday()].capitalize()
            temp_max_d = forecast["daily"]["temp_max"][i]
            temp_min_d = forecast["daily"]["temp_min"][i]
            weather = forecast["daily"]["weather_description"][i]
            emoji = WEATHER_EMOJIS.get(weather, "🌡")
            response += f"  {label}: {emoji} {temp_min_d}°C / {temp_max_d}°C, {weather}\n"

        response += f"\n\n_This forecast uses the last location you sent me. Send a new location to update it._"
        return response

    async def send_weather_alert(self, discussion_id: int):
        discussion = await self.discussion_get(discussion_id)
        if discussion:
            latitude, longitude = await self.get_location_for_discussion(discussion_id)
            if latitude and longitude:
                forecast = get_weather_forecast(latitude, longitude)
                if forecast:
                    timezone = forecast.get("timezone", "UTC")
                    tz = ZoneInfo(timezone)
                    response = self.format_forecast(forecast, tz)
                    await discussion.post_message(client=self, body=response)
                else:
                    await discussion.post_message(client=self, body="Failed to fetch weather data.")

    async def on_message_received(self, message: datatypes.Message):
        # Evelyne receives a location message.
        if hasattr(message, "message_location") and message.message_location:
            latitude = message.message_location.latitude
            longitude = message.message_location.longitude
            await self.store_location_for_discussion(message.discussion_id, latitude, longitude)
            forecast = get_weather_forecast(latitude, longitude)
            if forecast:
                timezone = forecast.get("timezone", "UTC")
                tz = ZoneInfo(timezone)
                response = self.format_forecast(forecast, tz)
                await message.reply(client=self, body=response)
            else:
                await message.reply(client=self, body="Failed to fetch weather data.")
        # Evelyne receives a HH:mm message.
        elif message.body and message.body.strip().count(":") == 1 and all(c.isdigit() or c == ":" for c in message.body.strip()):
            try:
                hour, minute = map(int, message.body.strip().split(":"))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    time_str = message.body.strip()
                    await self.store_scheduled_time_for_discussion(message.discussion_id, time_str)
                    self.scheduler.add_job(
                        self.send_weather_alert,
                        CronTrigger(hour=hour, minute=minute, timezone="UTC"),
                        args=[message.discussion_id],
                        id=f"weather_alert_{message.discussion_id}",
                        replace_existing=True
                    )
                    await message.reply(client=self, body=f"⏰ Daily weather alerts set for {message.body.strip()} UTC!")
                else:
                    await message.reply(client=self, body="❌ Invalid time format. Use HH:mm (24h format).")
            except ValueError:
                await message.reply(client=self, body="❌ Invalid time format. Use HH:mm (24h format).")

    async def on_discussion_new(self, discussion: datatypes.Discussion):
        title = discussion.title or ""
        first_name = title.split(" (")[0].split(" ")[0] if title else "there"
        await discussion.post_message(
            client=self,
            body=f"Hello {first_name}! 🤖🌤️ I'm Evelyne, your new weather forecast assistant. \n\n"
                 f"👉 Share a location to receive weather information for this location\n\n"
                 f"👉 Send me HH:mm (24h format, UTC timezone) to start receiving daily weather alerts at this time for the last location you sent (default time is 09:00)\n"
        )

async def main():
    evelyne = Evelyne()
    await evelyne.set_message_retention_policy(global_count=100, discussion_count=20, existence_duration=60 * 60 * 24 * 7, clean_locked_discussions=True)
    await evelyne.enable_auto_invitation(accept_all=True)
    await evelyne.restore_data()
    await evelyne.run_forever()

asyncio.set_event_loop(asyncio.new_event_loop())
asyncio.get_event_loop().run_until_complete(main())
