# -- coding: utf-8 --
"""Feishu integration test helper.

Usage examples:
  python test_feishu_webhook.py verify
  python test_feishu_webhook.py event --text "帮我规划北京3天行程"
  python test_feishu_webhook.py send --open-id ou_xxx --text "你好，这是联调消息"
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_env_file() -> None:
    """Load simple KEY=VALUE pairs from backend/.env if present."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

DEFAULT_BASE_URL = os.getenv("FEISHU_WEBHOOK_URL", "http://localhost:8000/api/feishu/webhook")
DEFAULT_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")


def post_json(
    url: str, payload: Dict[str, Any], timeout: int = 15, headers: Dict[str, str] | None = None
) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req_headers = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        req_headers.update(headers)
    request = Request(url=url, data=body, headers=req_headers, method="POST")

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.getcode(), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"Request failed: {exc}") from exc


def test_url_verification(base_url: str, token: str, challenge: str) -> None:
    payload = {
        "type": "url_verification",
        "token": token,
        "challenge": challenge,
    }
    status, body = post_json(base_url, payload)
    print("[verify] status:", status)
    print("[verify] body  :", body)


def test_message_event(base_url: str, token: str, open_id: str, text: str) -> None:
    payload = {
        "schema": "2.0",
        "header": {
            "event_type": "im.message.receive_v1",
            "token": token,
            "create_time": str(int(time.time() * 1000)),
            "event_id": f"evt_test_{int(time.time())}",
        },
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": open_id,
                }
            },
            "message": {
                "message_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        },
    }
    status, body = post_json(base_url, payload)
    print("[event] status:", status)
    print("[event] body  :", body)


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    if not app_id or not app_secret:
        raise ValueError("Missing FEISHU_APP_ID or FEISHU_APP_SECRET")

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}

    status, body = post_json(url, payload)
    if status != 200:
        raise RuntimeError(f"Get token failed: status={status}, body={body}")
    data = json.loads(body)
    if data.get("code") != 0:
        raise RuntimeError(f"Get token failed: {data}")

    return data["tenant_access_token"]


def send_text_message(open_id: str, text: str, app_id: str, app_secret: str) -> None:
    token = get_tenant_access_token(app_id, app_secret)
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "receive_id": open_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }

    status, body = post_json(url, payload, headers=headers)
    print("[send] status:", status)
    print("[send] body  :", body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Feishu webhook/direct-message test helper")
    parser.add_argument("mode", choices=["verify", "event", "send"], help="Test mode")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Webhook url")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Feishu verification token")
    parser.add_argument("--challenge", default="test_challenge_123", help="Challenge text for verify")
    parser.add_argument("--open-id", default="ou_test_open_id", help="Target open_id")
    parser.add_argument("--text", default="帮我规划一个去杭州3天的旅行", help="Message text")
    parser.add_argument("--app-id", default=FEISHU_APP_ID, help="Feishu app id")
    parser.add_argument("--app-secret", default=FEISHU_APP_SECRET, help="Feishu app secret")
    args = parser.parse_args()

    if args.mode in {"verify", "event"} and not args.token:
        raise ValueError("Missing token. Set FEISHU_VERIFICATION_TOKEN or pass --token")

    if args.mode == "verify":
        test_url_verification(args.url, args.token, args.challenge)
    elif args.mode == "event":
        test_message_event(args.url, args.token, args.open_id, args.text)
    else:
        send_text_message(args.open_id, args.text, args.app_id, args.app_secret)


if __name__ == "__main__":
    main()
