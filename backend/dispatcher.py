import hashlib
import hmac
import json
import logging
import threading
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 3, 9]


def _sign(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return "sha256=" + mac.hexdigest()


def _deliver(webhook_url: str, secret: str, body: bytes, sig: str) -> bool:
    for attempt, delay in enumerate(BACKOFF_SECONDS[:MAX_RETRIES], 1):
        try:
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Relay-Signature": sig,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if 200 <= resp.status < 300:
                    logger.info("Webhook delivered to %s (attempt %d)", webhook_url, attempt)
                    return True
        except Exception as exc:
            logger.warning("Webhook attempt %d to %s failed: %s", attempt, webhook_url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(delay)
    logger.error("Webhook delivery failed after %d attempts: %s", MAX_RETRIES, webhook_url)
    return False


def fire(webhook_url: str, secret: str, event: dict) -> None:
    """Fire-and-forget webhook delivery in a background thread."""
    body = json.dumps(event, default=str).encode()
    sig = _sign(secret, body)
    threading.Thread(target=_deliver, args=(webhook_url, secret, body, sig), daemon=True).start()
