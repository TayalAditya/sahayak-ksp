"""
Sahayak — Catalyst Basic I/O Function.
Accepts a JSON body via the 'input' argument, routes to the NL→SQL engine,
and returns the result as JSON.
"""
import sys, os, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)


def handler(context, basicio):
    try:
        raw = basicio.get_argument("input") or "{}"
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})
        action = body.get("action", "health")

        if action == "health":
            result = {"status": "ok", "service": "sahayak-backend"}

        elif action == "chat":
            from backend.engine import config, llm
            from backend.engine.conversation import Session
            config.load_dotenv()
            question = body.get("question", "").strip()
            provider = llm.get_provider()
            session = Session()
            res = session.ask(question, provider=provider)
            result = {
                "question": question,
                "sql": res.sql,
                "columns": res.columns,
                "rows": res.rows[:50],
                "row_count": res.row_count,
                "error": res.error,
            }

        elif action == "hotspots":
            from backend.engine import config
            config.load_dotenv()
            from backend.tools.hotspots import get_hotspots
            result = get_hotspots(crime_head=body.get("crime_head"))

        elif action == "trends":
            from backend.engine import config
            config.load_dotenv()
            from backend.tools.hotspots import get_trends
            result = get_trends(crime_head=body.get("crime_head"), group_by=body.get("group_by", "month"))

        elif action == "network":
            from backend.engine import config
            config.load_dotenv()
            from backend.tools.network import get_network
            result = get_network(crime_head=body.get("crime_head"), gang_name=body.get("gang_name"))

        else:
            result = {"error": f"Unknown action: {action}"}

        basicio.write(json.dumps(result))
    except Exception as e:
        basicio.write(json.dumps({"error": str(e)}))
    finally:
        context.close()
