import asyncio
import os
from flask import Flask, jsonify, request, send_file
import httpx
import requests


def create_app() -> Flask:
    app = Flask(__name__)

    # 1. Downstream Service Configuration
    app.config["USERS_SERVICE_URL"] = os.environ.get(
        "USERS_SERVICE_URL", "http://127.0.0.1:5001"
    )
    app.config["RECIPES_SERVICE_URL"] = os.environ.get(
        "RECIPES_SERVICE_URL", "http://127.0.0.1:5002"
    )
    app.config["INTERNAL_SERVICE_TOKEN"] = os.environ.get(
        "INTERNAL_SERVICE_TOKEN", "dev-internal-secret"
    )

    # 2. Downstream Async Fetch Helper with Graceful Fallback
    async def fetch_downstream(
        client: httpx.AsyncClient, url: str, headers: dict
    ) -> dict:
        try:
            resp = await asyncio.wait_for(
                client.get(url, headers=headers), timeout=2.0
            )
            if resp.status_code == 200:
                return {"status": "ok", "reason": None, "data": resp.json()}
            return {
                "status": "fallback",
                "reason": f"http_{resp.status_code}",
                "data": None,
            }
        except asyncio.TimeoutError:
            return {"status": "fallback", "reason": "timeout", "data": None}
        except httpx.RequestError:
            return {"status": "fallback", "reason": "error", "data": None}

    # 3. Frontend Static Route (searches root, app/, and gateway/)
    @app.route("/", methods=["GET"])
    def home():
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        # 1. Project root: /recipe-box-api/index.html
        root_path = os.path.join(root_dir, "index.html")
        if os.path.exists(root_path):
            return send_file(root_path)

        # 2. Inside app package: /recipe-box-api/app/index.html
        app_path = os.path.join(root_dir, "app", "index.html")
        if os.path.exists(app_path):
            return send_file(app_path)

        # 3. Inside gateway package: /recipe-box-api/gateway/index.html
        gateway_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "index.html")
        )
        if os.path.exists(gateway_path):
            return send_file(gateway_path)

        return (
            jsonify({"message": "Gateway active, index.html not found"}),
            404,
        )

    # 4. Gateway Health Check
    @app.route("/health", methods=["GET"])
    def health():
        token = app.config.get("INTERNAL_SERVICE_TOKEN", "")
        masked_token = (
            f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "***"
        )
        return (
            jsonify(
                {
                    "status": "ok",
                    "users_service_url": app.config["USERS_SERVICE_URL"],
                    "recipes_service_url": app.config["RECIPES_SERVICE_URL"],
                    "internal_service_token": masked_token,
                }
            ),
            200,
        )

    # 5. Composed Concurrent Endpoint
    @app.route("/me/recipes", methods=["GET"])
    async def me_recipes():
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Missing or invalid token",
                    }
                ),
                401,
            )

        users_url = f"{app.config['USERS_SERVICE_URL']}/me"
        recipes_url = f"{app.config['RECIPES_SERVICE_URL']}/recipes"

        users_headers = {"Authorization": auth_header}
        recipes_headers = {
            "Authorization": auth_header,
            "X-Internal-Service-Token": app.config["INTERNAL_SERVICE_TOKEN"],
        }

        async with httpx.AsyncClient() as client:
            user_res, recipes_res = await asyncio.gather(
                fetch_downstream(client, users_url, users_headers),
                fetch_downstream(client, recipes_url, recipes_headers),
            )

        payload = {
            "user": user_res["data"],
            "recipes": recipes_res["data"],
            "_meta": {
                "user": {
                    "status": user_res["status"],
                    "reason": user_res["reason"],
                },
                "recipes": {
                    "status": recipes_res["status"],
                    "reason": recipes_res["reason"],
                },
            },
        }
        return jsonify(payload), 200

    # 6. Public Auth Pass-Through Routes
    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json(silent=True) or {}
        users_url = f"{app.config['USERS_SERVICE_URL']}/login"

        try:
            resp = requests.post(users_url, json=data, timeout=5.0)
            return (resp.content, resp.status_code, resp.headers.items())
        except requests.RequestException:
            return jsonify({"error": "Users service unavailable"}), 503

    @app.route("/register", methods=["POST"])
    def register():
        data = request.get_json(silent=True) or {}
        users_url = f"{app.config['USERS_SERVICE_URL']}/register"

        try:
            resp = requests.post(users_url, json=data, timeout=5.0)
            return (resp.content, resp.status_code, resp.headers.items())
        except requests.RequestException:
            return jsonify({"error": "Users service unavailable"}), 503

    return app