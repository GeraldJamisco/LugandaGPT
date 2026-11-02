"""HTTP client for Sunbird's OpenAI-style Sunflower chat endpoint.

Standard library only, matching the project's minimal-dependency rule. The
token is read from the environment, kept in memory, and never written to disk,
logs, error messages, or the usage ledger. The ledger stores a hash of each
prompt, not its text, so it can be committed.

Endpoint and model names follow docs.sunbird.ai (read 2026-11-02):
POST /tasks/chat/completions with model "sunflower-9b" or "sunflower-14b".
Pricing and rate limits are not published there, so every client carries a
request cap that the caller must raise on purpose.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://api.sunbird.ai"
CHAT_PATH = "/tasks/chat/completions"
TOKEN_PATH = "/auth/token"
ME_PATH = "/auth/me"
MODELS = ("sunflower-9b", "sunflower-14b")
DEFAULT_MODEL = "sunflower-14b"
ROLES = ("system", "user", "assistant")
ENV_TOKEN = "SUNBIRD_API_TOKEN"
ENV_USERNAME = "SUNBIRD_USERNAME"
ENV_PASSWORD = "SUNBIRD_PASSWORD"
RETRY_STATUS = (429, 502, 503, 504)
MAX_ERROR_TEXT = 300
MAX_BACKOFF_SECONDS = 30
USER_AGENT = "LugandaGPT-research/0.1"


class SunbirdError(Exception):
    """Base class for every error this client raises."""


class ConfigError(SunbirdError):
    """Missing credentials or an argument the API would reject."""


class AuthError(SunbirdError):
    """The API rejected the token."""


class BudgetGuardError(SunbirdError):
    """The request cap for this client was reached."""


class ApiError(SunbirdError):
    def __init__(self, status, message):
        super().__init__(f"Sunbird API returned HTTP {status}: {message}")
        self.status = status


@dataclass
class ChatResult:
    text: str
    model: str
    finish_reason: str
    usage: dict
    response_id: str
    latency_s: float
    temperature: float
    attempts: int = 1
    raw_keys: list = field(default_factory=list)


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_sha256(messages):
    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SunbirdClient:
    def __init__(
        self,
        token=None,
        *,
        username=None,
        password=None,
        base_url=BASE_URL,
        timeout=120,
        max_retries=3,
        request_cap=25,
        ledger_path=None,
        opener=None,
        sleep=time.sleep,
    ):
        self._token = token if token is not None else os.environ.get(ENV_TOKEN)
        self._username = username if username is not None else os.environ.get(ENV_USERNAME)
        self._password = password if password is not None else os.environ.get(ENV_PASSWORD)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_cap = request_cap
        self.requests_made = 0
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self._urlopen = opener or urllib.request.urlopen
        self._sleep = sleep

    def __repr__(self):
        return f"SunbirdClient(base_url={self.base_url!r}, requests_made={self.requests_made})"

    # -- credentials -------------------------------------------------------

    def _can_login(self):
        return bool(self._username and self._password)

    def _require_token(self):
        if not self._token and self._can_login():
            self._login()
        if not self._token:
            raise ConfigError(
                f"no Sunbird credentials: set {ENV_TOKEN}, or {ENV_USERNAME} and "
                f"{ENV_PASSWORD}, in the environment"
            )
        return self._token

    def _login(self):
        body = urllib.parse.urlencode(
            {"username": self._username, "password": self._password}
        ).encode("utf-8")
        _, raw, _, _ = self._send(
            "POST",
            TOKEN_PATH,
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            authed=False,
        )
        token = self._json(raw).get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthError("login response did not include an access token")
        self._token = token

    # -- transport ---------------------------------------------------------

    @staticmethod
    def _json(raw):
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise SunbirdError("response was not valid JSON") from None
        if not isinstance(value, dict):
            raise SunbirdError("response JSON was not an object")
        return value

    def _delay(self, attempt, retry_after):
        if retry_after:
            try:
                return min(float(retry_after), MAX_BACKOFF_SECONDS)
            except ValueError:
                pass
        return min(2 ** (attempt - 1), MAX_BACKOFF_SECONDS)

    def _api_error(self, status, raw):
        text = raw.decode("utf-8", errors="replace").strip()
        return ApiError(status, text[:MAX_ERROR_TEXT] or "no body")

    def _send(self, method, path, *, body=None, headers=None, authed=True):
        url = self.base_url + path
        attempt = 0
        relogged = False
        while True:
            attempt += 1
            request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
            request_headers.update(headers or {})
            if authed:
                request_headers["Authorization"] = "Bearer " + self._require_token()
            request = urllib.request.Request(
                url, data=body, method=method, headers=request_headers
            )
            started = time.monotonic()
            try:
                with self._urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    status = response.status
                return status, raw, time.monotonic() - started, attempt
            except urllib.error.HTTPError as error:
                status = error.code
                raw = error.read() if hasattr(error, "read") else b""
                retry_after = error.headers.get("Retry-After") if error.headers else None
                if status == 401 and authed:
                    # A password login can mint a fresh token; a bare token cannot.
                    if self._can_login() and not relogged:
                        relogged = True
                        self._token = None
                        continue
                    raise AuthError(
                        "Sunbird rejected the token (HTTP 401); get a new one from /auth/token"
                    ) from None
                if status in RETRY_STATUS and attempt <= self.max_retries:
                    self._sleep(self._delay(attempt, retry_after))
                    continue
                raise self._api_error(status, raw) from None
            except urllib.error.URLError as error:
                if attempt <= self.max_retries:
                    self._sleep(self._delay(attempt, None))
                    continue
                raise SunbirdError(f"network error: {error.reason}") from None

    # -- ledger ------------------------------------------------------------

    def _ledger(self, record):
        if not self.ledger_path:
            return
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    # -- public calls ------------------------------------------------------

    def check(self):
        """Confirm the token works. Returns the account fields the API reports."""
        _, raw, _, _ = self._send("GET", ME_PATH)
        return self._json(raw)

    def chat(
        self,
        messages,
        *,
        model=DEFAULT_MODEL,
        temperature=0.3,
        max_tokens=None,
        top_p=None,
        stop=None,
        purpose="",
    ):
        self._validate_chat(messages, model, temperature, max_tokens)
        if self.request_cap is not None and self.requests_made >= self.request_cap:
            raise BudgetGuardError(
                f"request cap of {self.request_cap} reached; raise it on purpose to continue"
            )
        payload = {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.requests_made += 1
        base = {
            "created_utc": _utc_now(),
            "endpoint": CHAT_PATH,
            "model": model,
            "purpose": purpose,
            "prompt_sha256": prompt_sha256(payload["messages"]),
        }
        try:
            _, raw, latency, attempts = self._send(
                "POST", CHAT_PATH, body=body, headers={"Content-Type": "application/json"}
            )
            data = self._json(raw)
            result = self._parse_chat(data, model, temperature, latency, attempts)
        except SunbirdError as error:
            status = getattr(error, "status", None)
            self._ledger({**base, "outcome": type(error).__name__, "http_status": status})
            raise
        self._ledger(
            {
                **base,
                "outcome": "ok",
                "http_status": 200,
                "finish_reason": result.finish_reason,
                "latency_s": round(latency, 3),
                "attempts": attempts,
                **{k: result.usage.get(k, 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
            }
        )
        return result

    def translate(
        self,
        text,
        *,
        model=DEFAULT_MODEL,
        temperature=0.3,
        max_tokens=512,
        purpose="translate",
    ):
        """English to Luganda, phrased the way Sunbird's own examples ask for it."""
        if not isinstance(text, str) or not text.strip():
            raise ConfigError("text to translate must be a non-empty string")
        messages = [
            {"role": "user", "content": f"Translate from English to Luganda: {text.strip()}"}
        ]
        return self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            purpose=purpose,
        )

    # -- validation and parsing -------------------------------------------

    @staticmethod
    def _validate_chat(messages, model, temperature, max_tokens):
        if model not in MODELS:
            raise ConfigError(f"model must be one of {', '.join(MODELS)}; got {model!r}")
        if not isinstance(messages, (list, tuple)) or not messages:
            raise ConfigError("messages must be a non-empty list")
        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in ROLES
                or not isinstance(message.get("content"), str)
                or not message["content"].strip()
            ):
                raise ConfigError("each message needs a valid role and non-empty text content")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            raise ConfigError("temperature must be between 0 and 2")
        if max_tokens is not None and (isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1):
            raise ConfigError("max_tokens must be a positive integer")

    @staticmethod
    def _parse_chat(data, requested_model, temperature, latency, attempts):
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise SunbirdError("unexpected chat response shape") from None
        if not isinstance(text, str):
            raise SunbirdError("unexpected chat response shape")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return ChatResult(
            text=text.strip(),
            model=str(data.get("model") or requested_model),
            finish_reason=str(choice.get("finish_reason") or ""),
            usage={k: int(v) for k, v in usage.items() if isinstance(v, (int, float))},
            response_id=str(data.get("id") or ""),
            latency_s=latency,
            temperature=temperature,
            attempts=attempts,
            raw_keys=sorted(data.keys()),
        )
