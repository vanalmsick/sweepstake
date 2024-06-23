# -*- coding: utf-8 -*-
import requests
import os
import datetime

API_HEADERS = {
    "x-rapidapi-key": os.environ.get("API_KEY_FOOTBALL_SCORES", ""),
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
}


def __api_limit(api_limit=100):
    """API limit of 100 requests per day"""
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    api_requests = os.environ.get("API_REQUESTS_FOOTBALL_SCORES", {})

    if today not in api_requests:
        api_requests[today] = 0

    if api_requests[today] < api_limit:
        api_requests[today] += 1
        return True
    else:
        print("Football API Request Limit reached - no more requests today!")
        return False


def get_api_match_ids(season_year):
    """get match list of tounament which also contains the match ids"""
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

    querystring = {
        "league": "4",  # UEFA EURO
        "season": str(season_year),
    }

    if __api_limit():
        response = requests.get(url, headers=API_HEADERS, params=querystring)
        all_match_data = response.json()

        return all_match_data["response"] if "response" in all_match_data else None

    else:
        return None


def get_api_match_data(match_id):
    """get match result and statistics via API"""
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

    querystring = {"id": str(match_id)}

    if __api_limit():
        response = requests.get(url, headers=API_HEADERS, params=querystring)
        match_data = response.json()

        return match_data["response"][0] if "response" in match_data else None

    else:
        return None
