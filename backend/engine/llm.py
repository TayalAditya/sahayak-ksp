"""
Pluggable LLM provider.  One interface, three backends:

  mock           deterministic — returns canned SQL for the demo questions. No creds, no
                 network. Lets us build & test the whole pipeline before Qwen is wired.
  ollama-qwen    local Qwen via Ollama (http://localhost:11434) — dev parity with prod.
  catalyst-qwen  Catalyst QuickML LLM-serving endpoint (Qwen 2.5) — PRODUCTION.

Select via the LLM_PROVIDER env var (see .env.example). The rest of the engine only ever
calls `get_provider().complete(system, user, ...)`, so swapping backends is a config change.
"""

import json
import re
import urllib.parse
import urllib.request

from . import config


class LLMProvider:
    name = "base"

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=512):
        raise NotImplementedError


# --------------------------------------------------------------------------- mock
class MockProvider(LLMProvider):
    """Returns canned SQL by keyword-matching the question. Pipeline-testable, no model."""

    name = "mock"

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=512):
        q = user_prompt.lower()

        def has(*words):
            return all(w in q for w in words)

        if has("how many", "theft") or has("count", "theft"):
            return "SELECT COUNT(*) AS theft_cases FROM firs WHERE crime_head = 'Theft';"
        if has("repeat offender") or has("habitual"):
            return (
                "SELECT p.id, p.full_name, COUNT(*) AS cases "
                "FROM fir_persons fp JOIN persons p ON p.id = fp.person_id "
                "WHERE fp.role = 'Accused' GROUP BY p.id ORDER BY cases DESC LIMIT 10;"
            )
        if has("top", "district") or has("most", "district"):
            return (
                "SELECT d.name AS district, COUNT(*) AS firs "
                "FROM firs f JOIN districts d ON d.id = f.district_id "
                "GROUP BY d.id ORDER BY firs DESC LIMIT 10;"
            )
        if has("hotspot") or has("police station", "most"):
            return (
                "SELECT ps.name AS station, COUNT(*) AS firs "
                "FROM firs f JOIN police_stations ps ON ps.id = f.police_station_id "
                "GROUP BY ps.id ORDER BY firs DESC LIMIT 10;"
            )
        if has("trend") or has("per year") or has("by year"):
            return (
                "SELECT substr(occurrence_date,1,4) AS year, COUNT(*) AS firs "
                "FROM firs GROUP BY year ORDER BY year;"
            )
        if has("bail"):
            return (
                "SELECT bail_status, COUNT(*) AS n FROM arrests "
                "GROUP BY bail_status ORDER BY n DESC;"
            )
        # default: crime distribution
        return (
            "SELECT crime_head, COUNT(*) AS firs FROM firs "
            "GROUP BY crime_head ORDER BY firs DESC LIMIT 10;"
        )


# --------------------------------------------------------------------------- ollama
class OllamaProvider(LLMProvider):
    name = "ollama-qwen"

    def __init__(self, model=None, host=None):
        self.model = model or config.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.host = host or config.get("OLLAMA_HOST", "http://localhost:11434")

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=512):
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return data["message"]["content"]


# --------------------------------------------------------------------------- catalyst qwen
class CatalystQwenProvider(LLMProvider):
    """
    Calls Catalyst QuickML LLM-serving endpoint.
    Both Qwen models use the SAME endpoint URL; model is selected via the "model" field
    in the request body (confirmed: same URL returned for 7B Coder and 14B Instruct).

    Mints a short-lived OAuth access token from the stored refresh token; auto-refreshes on 401.
    """

    name = "catalyst-qwen"

    def __init__(self, model=None):
        self.dc = config.get("ZOHO_DC", "in")
        self.endpoint = config.get("QWEN_LLM_ENDPOINT")
        self.org_id = config.get("ZOHO_ORG_ID")
        self.client_id = config.get("ZOHO_CLIENT_ID")
        self.client_secret = config.get("ZOHO_CLIENT_SECRET")
        self.refresh_token = config.get("ZOHO_REFRESH_TOKEN")
        # Default to coder (NL→SQL); pass model="instruct" for summaries/chat.
        self._model_key = model or "coder"
        self._access_token = None

    @property
    def model_name(self):
        if self._model_key == "instruct":
            return config.get("QWEN_INSTRUCT_MODEL", "qwen2.5-14b-instruct")
        return config.get("QWEN_CODER_MODEL", "qwen2.5-coder-7b")

    def _refresh_access_token(self):
        url = f"https://accounts.zoho.{self.dc}/oauth/v2/token"
        payload = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }).encode()
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        if "access_token" not in data:
            raise RuntimeError(f"OAuth refresh failed: {data}")
        self._access_token = data["access_token"]

    def _extract_text(self, data):
        # Catalyst QuickML response shape (confirmed): {"response": "...", "usage": {...}, ...}
        if isinstance(data, dict) and "response" in data:
            return data["response"]
        return json.dumps(data)

    def _call(self, body_bytes, headers):
        req = urllib.request.Request(self.endpoint, data=body_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return self._extract_text(json.loads(resp.read().decode()))

    def complete(self, system_prompt, user_prompt, temperature=0.0, max_tokens=1024):
        if not self._access_token:
            self._refresh_access_token()
        body = json.dumps({
            "model": self.model_name,
            "prompt": user_prompt,
            "system_prompt": system_prompt,
            "top_p": 0.9,
            "top_k": 50,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode()
        headers = {
            "Authorization": f"Zoho-oauthtoken {self._access_token}",
            "Content-Type": "application/json",
            "CATALYST-ORG": self.org_id or "",
        }
        try:
            return self._call(body, headers)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                self._refresh_access_token()
                headers["Authorization"] = f"Zoho-oauthtoken {self._access_token}"
                return self._call(body, headers)
            raise


# --------------------------------------------------------------------------- factory
def get_provider(name=None, model=None):
    name = name or config.LLM_PROVIDER
    if name == "mock":
        return MockProvider()
    if name == "ollama-qwen":
        return OllamaProvider()
    if name == "catalyst-qwen":
        return CatalystQwenProvider(model=model)  # model="coder" (default) or "instruct"
    raise ValueError(f"unknown LLM_PROVIDER '{name}'")
