from __future__ import annotations

from http import HTTPStatus
import os

from flask import Flask, jsonify, make_response, request, send_from_directory

from Dashboard.server import (
    _ACCESS_CODE,
    _COOKIE_NAME,
    _COOKIE_VALUE,
    build_match_brief_response,
    build_scenario_response,
    fetch_live_score,
    handle_demo_request,
)

app = Flask(__name__)


def _is_authenticated() -> bool:
    return request.cookies.get(_COOKIE_NAME, "") == _COOKIE_VALUE


@app.get("/api")
def api_root():
    return jsonify({"ok": True, "service": "creaseiq-api"})


@app.post("/api/auth")
def api_auth():
    payload = request.get_json(silent=True) or {}
    if payload.get("code") != _ACCESS_CODE:
        return jsonify({"ok": False}), HTTPStatus.UNAUTHORIZED

    response = make_response(jsonify({"ok": True}), HTTPStatus.OK)
    response.set_cookie(
        _COOKIE_NAME,
        _COOKIE_VALUE,
        max_age=43200,
        httponly=True,
        samesite="Lax",
        secure=bool(os.environ.get("VERCEL")),
        path="/",
    )
    return response


@app.post("/api/demo-request")
def api_demo_request():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(handle_demo_request(payload))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@app.post("/api/run-scenario")
def api_run_scenario():
    if not _is_authenticated():
        return jsonify({"error": "Not authenticated"}), HTTPStatus.UNAUTHORIZED
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(build_scenario_response(payload))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@app.post("/api/match-brief")
def api_match_brief():
    if not _is_authenticated():
        return jsonify({"error": "Not authenticated"}), HTTPStatus.UNAUTHORIZED
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(build_match_brief_response(payload))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@app.get("/api/live-score")
def api_live_score_get():
    if not _is_authenticated():
        return jsonify({"error": "Not authenticated"}), HTTPStatus.UNAUTHORIZED
    try:
        return jsonify(fetch_live_score())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@app.post("/api/live-score")
def api_live_score_post():
    if not _is_authenticated():
        return jsonify({"error": "Not authenticated"}), HTTPStatus.UNAUTHORIZED
    try:
        return jsonify(fetch_live_score())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path):
    if not path or path == "/":
        path = "illuminated_hero.html"
    elif path.startswith("Dashboard/"):
        path = path[len("Dashboard/"):]
        
    dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dashboard")
    file_path = os.path.join(dashboard_dir, path)
    
    if os.path.exists(file_path):
        return send_from_directory(dashboard_dir, path)
        
    return make_response("Not Found", 404)
