"""Live NL→SQL test: Qwen Coder generates SQL, verified, executed on crime DB."""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.engine import config, llm
from backend.engine.nl2sql import ask
config.load_dotenv()

provider = llm.get_provider("catalyst-qwen", model="coder")

QUESTIONS = [
    "How many theft cases are there in total?",
    "Which district has the most FIRs?",
    "Show me the top 5 repeat offenders",
    "What is the trend of FIRs by year?",
    "How many cases are currently under investigation?",
]

print(f"\n{'='*70}")
print("Sahayak — Live NL→SQL (Qwen Coder on Catalyst QuickML)")
print(f"{'='*70}\n")

for q in QUESTIONS:
    print(f"Q: {q}")
    result = ask(q, provider=provider)
    if result.error:
        print(f"  ERROR: {result.error}")
    else:
        print(f"  SQL: {result.sql}")
        print(f"  Rows ({result.row_count}):", json.dumps(result.rows[:3], ensure_ascii=False))
    print()
