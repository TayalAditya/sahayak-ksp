"""
Multi-turn conversation session.

Keeps the last N turns as context so follow-up questions like
"show me only the ones in Bengaluru" work without repeating the full context.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .nl2sql import ask, NL2SQLResult


MAX_CONTEXT_TURNS = 4


@dataclass
class Turn:
    question: str
    sql: Optional[str]
    row_count: int
    error: Optional[str]
    answer_summary: str    # one-line summary fed back as context


@dataclass
class Session:
    user_id: Optional[int] = None
    role: str = "Investigator"
    turns: List[Turn] = field(default_factory=list)

    def _context_block(self):
        if not self.turns:
            return ""
        recent = self.turns[-MAX_CONTEXT_TURNS:]
        lines = []
        for t in recent:
            lines.append(f"Q: {t.question}")
            if t.sql:
                lines.append(f"SQL: {t.sql}")
            lines.append(f"Result: {t.answer_summary}")
        return "\n".join(lines)

    def ask(self, question, provider=None):
        result: NL2SQLResult = ask(
            question,
            provider=provider,
            conversation_context=self._context_block(),
        )
        if result.error:
            summary = f"Error: {result.error}"
        elif result.row_count == 0:
            summary = "No records found."
        elif result.row_count == 1 and result.rows:
            summary = str(result.rows[0])
        else:
            summary = f"{result.row_count} records returned."

        self.turns.append(Turn(
            question=question,
            sql=result.sql,
            row_count=result.row_count,
            error=result.error,
            answer_summary=summary,
        ))
        return result
