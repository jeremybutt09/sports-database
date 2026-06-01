from __future__ import annotations

import requests


def fetch_endpoint(url: str) -> dict:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
