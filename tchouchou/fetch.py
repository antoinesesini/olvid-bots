import difflib
import os

import pytz
import requests
from datetime import datetime
from dotenv import load_dotenv
import json
import argparse

load_dotenv()


with open("data/line_mapping.json", "r", encoding="utf-8") as f:
    lines = json.load(f)

with open("data/stop_mapping.json", "r", encoding="utf-8") as f:
    stops = json.load(f)

def get_next_trains(monitoring_ref, line_id, api_url, api_key):
    """
    Fetches and returns the next trains for a given monitoring reference and line ID.

    Args:
        monitoring_ref (str): The MonitoringRef ID (e.g., "STIF:StopArea:SP:63923:").
        line_id (str): The STIF line ID (e.g., "STIF:Line::C01736:").
        api_url (str): The API endpoint URL.
        api_key (str): The API key for authentication.

    Returns:
        list: A list of dictionaries containing train information.
    """
    headers = {
        "apiKey": api_key
    }
    params = {
        "MonitoringRef": monitoring_ref
    }

    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

    utc_timezone = pytz.UTC
    local_timezone = pytz.timezone('Europe/Paris')
    next_trains = []
    for visit in data["Siri"]["ServiceDelivery"]["StopMonitoringDelivery"][0]["MonitoredStopVisit"]:
        try:
            line_ref = visit["MonitoredVehicleJourney"]["LineRef"]["value"]
            if line_ref == line_id:
                destination = visit["MonitoredVehicleJourney"]["DestinationName"][0]["value"]
                direction = visit["MonitoredVehicleJourney"]["DirectionRef"]["value"]

                monitored_call = visit["MonitoredVehicleJourney"].get("MonitoredCall")
                if not monitored_call:
                    continue

                expected_departure = monitored_call.get("ExpectedDepartureTime")
                if not expected_departure:
                    continue

                naive_departure_time = datetime.strptime(expected_departure, "%Y-%m-%dT%H:%M:%S.%fZ")
                utc_departure_time = utc_timezone.localize(naive_departure_time)
                local_departure_time = utc_departure_time.astimezone(local_timezone)

                next_trains.append({
                    "destination": destination,
                    "direction": direction,
                    "expected_departure": local_departure_time
                })
        except KeyError as e:
            print(f"Skipping an entry due to missing key: {e}")
            continue

    # Sort by expected departure time
    next_trains.sort(key=lambda x: x["expected_departure"])
    return next_trains

def display_next_trains(next_trains):
    """
    Displays the next trains in a user-friendly format.

    Args:
        next_trains (list): A list of dictionaries containing train information.
    """
    if not next_trains:
        print("No trains found for the specified line.")
        return

    print("Next trains:")
    for i, train in enumerate(next_trains, start=1):
        print(f"{i}. Destination: {train['destination']}")
        print(f"   Direction: {train['direction']}")
        print(f"   Expected Departure: {train['expected_departure'].strftime('%H:%M')}")
        print()

def suggest_stops(user_input, stops, max_suggestions=5):
    """
    Suggest stop names close to the user input.
    """
    return difflib.get_close_matches(
        user_input,
        stops.keys(),
        n=max_suggestions,
        cutoff=0.1
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Display the next trains for a given line and stop."
    )
    parser.add_argument(
        "--line",
        required=True,
        help="Line letter (ex: N, A, B, C)"
    )
    parser.add_argument(
        "--stop",
        required=True,
        help="Stop name (ex: 'Brancion - Morillons')"
    )
    args = parser.parse_args()
    stop_input = args.stop
    line_letter = args.line.upper()


    if line_letter not in lines:
        raise ValueError(f"Unknown line: {line_letter}")
    if stop_input not in stops:
        suggestions = suggest_stops(stop_input, stops)
        if not suggestions:
            raise ValueError(f"No stop found close to '{stop_input}'")
        print(f"Stop '{stop_input}' not found. Did you mean:\n")
        for i, stop in enumerate(suggestions, start=1):
            print(f"{i}. {stop}")
        choice = input("\nChoose a stop number (or press Enter to cancel): ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(suggestions)):
            print("Cancelled.")
            exit(1)
        stop_name = suggestions[int(choice) - 1]
    else:
        stop_name = stop_input

    MONITORING_REF = f"STIF:StopArea:SP:{stops[stop_name]}:"
    LINE_ID = f"STIF:Line::{lines[line_letter]}:"
    API_URL = os.getenv("API_URL")
    API_KEY = os.getenv("API_KEY")

    print(f"\nUsing stop: {stop_name}")
    print(f"Stop ref: {MONITORING_REF}")
    print(f"Line ref: {LINE_ID}\n")

    next_trains = get_next_trains(
        MONITORING_REF,
        LINE_ID,
        API_URL,
        API_KEY
    )

    display_next_trains(next_trains)
