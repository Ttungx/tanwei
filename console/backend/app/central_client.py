import os

import requests
from fastapi import HTTPException


CENTRAL_AGENT_URL = os.getenv("CENTRAL_AGENT_URL", "http://central-agent:8003")


def _handle_error(exc: requests.RequestException) -> HTTPException:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or "central-agent request failed"
        return HTTPException(status_code=response.status_code, detail=detail)

    return HTTPException(status_code=503, detail="central-agent unavailable")


def list_edges():
    try:
        response = requests.get(f"{CENTRAL_AGENT_URL}/api/v1/edges", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc


def get_latest_report(edge_id: str):
    try:
        response = requests.get(f"{CENTRAL_AGENT_URL}/api/v1/edges/{edge_id}/reports/latest", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc


def analyze_edge(edge_id: str):
    try:
        response = requests.post(f"{CENTRAL_AGENT_URL}/api/v1/edges/{edge_id}/analyze", timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc


def analyze_network():
    try:
        response = requests.post(f"{CENTRAL_AGENT_URL}/api/v1/network/analyze", timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc


def get_latest_edge_analysis(edge_id: str):
    try:
        response = requests.get(f"{CENTRAL_AGENT_URL}/api/v1/edges/{edge_id}/analysis", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc


def get_latest_network_analysis():
    try:
        response = requests.get(f"{CENTRAL_AGENT_URL}/api/v1/network/analysis", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise _handle_error(exc) from exc
