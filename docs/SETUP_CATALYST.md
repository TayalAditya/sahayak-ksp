# Catalyst Setup — what to do & what to hand me

Goal: get Sahayak talking to **Catalyst QuickML Qwen**. You do 5 short steps in the browser;
fill the values into `.env`; I wire up the rest. **Don't paste secrets into chat** — put them in
`.env` (it's gitignored). I'll read `.env` locally.

---

## Step 0 — Give Claude Code the Catalyst skill (do this first)
So I generate deployment-ready Catalyst code (correct SDK patterns, `catalyst-config.json`, etc.).
In your Claude Code session, type:

```
/plugin marketplace add catalystbyzoho/agent-skills
/plugin install catalyst-by-zoho@catalyst-by-zoho
```
*(If the marketplace string errors, check the exact one in the repo README:
https://github.com/catalystbyzoho/agent-skills )*

## Step 1 — Claim your hackathon credits (so you aren't charged)
Open the special link (coupon pre-filled): **https://catalyst.zoho.com/promotions.html?cn=KSPH26**
→ sign in → Proceed to redeem → Settings → Manage Billing → Basic plan → **tick "use my wallet
credit"** → Proceed. You get ₹2,500 + $250 in credits covering the whole hackathon.

## Step 2 — Create the project + note IDs
Catalyst console → **New Project** → name it `Sahayak` → Create.
Then grab → put in `.env`:
- **`CATALYST_PROJECT_ID`** — in the project URL / project settings.
- **`ZOHO_ORG_ID`** — your org/ZAID (Settings → look for Org/Portal ID).
- **`ZOHO_DC`** — `in` if your console URL is `*.zoho.in` (most India accounts), else `com`.

## Step 3 — Turn on Qwen + copy endpoint URLs
Console → **QuickML** → **Generative AI** → **LLM Serving** → **Models**.
For **each** of these, open it → **Model Details** → **API Details** → copy the endpoint URL:
- **Qwen 2.5 – 7B Coder**  → `.env` `QWEN_CODER_ENDPOINT`   (this powers NL→SQL)
- **Qwen 2.5 – 14B Instruct** → `.env` `QWEN_INSTRUCT_ENDPOINT` (summaries / chat / explanations)

*(Tip: open the Chat tab and send one prompt first, so the model is initialized.)*

## Step 4 — Create OAuth credentials
Open **https://api-console.zoho.{DC}** (e.g. `api-console.zoho.in`) → **Self Client** → Create.
- Copy **Client ID** → `.env` `ZOHO_CLIENT_ID`
- Copy **Client Secret** → `.env` `ZOHO_CLIENT_SECRET`
- Go to the **Generate Code** tab:
  - Scope: `QuickML.deployment.READ`
  - Time duration: 10 minutes · pick a portal if asked
  - **Create** → copy the **grant code** (use it within 10 min!)

## Step 5 — Turn the grant code into a refresh token
In a terminal (within 10 min of Step 4):

```bash
python tools/get_refresh_token.py \
  --dc in \
  --client-id   <ZOHO_CLIENT_ID> \
  --client-secret <ZOHO_CLIENT_SECRET> \
  --code        <GRANT_CODE>
```
It prints `ZOHO_REFRESH_TOKEN=...` → paste that into `.env`.

---

## When done, `.env` has all of:
```
ZOHO_DC, CATALYST_PROJECT_ID, ZOHO_ORG_ID,
ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN,
QWEN_CODER_ENDPOINT, QWEN_INSTRUCT_ENDPOINT
```
Tell me "env is filled" and I'll wire the `catalyst-qwen` provider + run the first real NL→SQL.

> Stuck on any step? I can fall back to the **mock** provider and build the entire engine now,
> then we slot Qwen in the moment your `.env` is ready — zero rework.
