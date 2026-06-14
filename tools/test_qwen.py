"""Final format check — use proper max_tokens values."""
import sys, os, json, urllib.request, urllib.error
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.engine import config, llm
config.load_dotenv()

provider = llm.get_provider("catalyst-qwen", model="coder")
provider._refresh_access_token()
token = provider._access_token
org = provider.org_id or ""
url = provider.endpoint
print(f"Token OK\n")

def post(label, payload):
    print(f"[{label}]")
    h = {"Authorization": f"Zoho-oauthtoken {token}",
         "Content-Type": "application/json", "CATALYST-ORG": org}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = resp.read().decode()
            print(f"  SUCCESS: {data[:800]}")
            return True
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:300]}")
        return False

# Instruct with large max_tokens (short prompt to stay within context)
post("instruct 14B - short prompt, max_tokens=512", {
    "model": "crm-di-qwen_text_14b-fp8-it",
    "prompt": "Say hello.",
    "system_prompt": "Be brief.",
    "top_p": 0.9, "top_k": 50, "temperature": 0.0, "max_tokens": 512,
})

# Coder with large max_tokens
post("coder 7B - short prompt, max_tokens=512", {
    "model": "crm-di-qwen_coder_7b-it",
    "prompt": "Write SELECT 1;",
    "system_prompt": "Return only SQL.",
    "top_p": 0.9, "top_k": 50, "temperature": 0.0, "max_tokens": 512,
})
