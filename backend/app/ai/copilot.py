"""The conversational Copilot: retrieve -> ground -> generate -> label."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai import gemini
from app.ai.context import build_station_context, context_to_prompt_block
from app.ai.prompts import COPILOT_SYSTEM
from app.core.errors import AIUnavailable
from app.db.models import City, Conversation, Message, Station, User

SUGGESTED_QUESTIONS = [
    "Why is the AQI high right now?",
    "Will pollution get worse tonight?",
    "What is causing the PM2.5 here?",
    "Is it safe to exercise outside?",
    "What can the city do about this today?",
    "What would happen if traffic dropped 30%?",
]

MAX_TURNS_IN_PROMPT = 6


def _history_block(conversation: Conversation | None) -> str:
    if not conversation or not conversation.messages:
        return ""
    recent = conversation.messages[-MAX_TURNS_IN_PROMPT * 2:]
    lines = [f"{m.role.upper()}: {m.content}" for m in recent]
    return "CONVERSATION SO FAR\n" + "\n".join(lines) + "\n\n"


def answer(db: Session, *, question: str, city: City, station: Station,
           forecasts: list | None = None, source_estimate=None,
           conversation: Conversation | None = None,
           user: User | None = None) -> dict:
    """Returns the answer plus the exact grounding it was given, so the UI can
    show the user what the model was allowed to see."""
    clean_question = gemini.sanitize_user_text(question)
    if not clean_question:
        raise AIUnavailable("Please ask a question.")

    context = build_station_context(db, city, station, forecasts=forecasts,
                                    source_estimate=source_estimate)
    prompt = (f"{_history_block(conversation)}"
              f"{context_to_prompt_block(context)}\n\n"
              f"USER QUESTION\n{clean_question}\n\n"
              f"Answer using only the grounded facts above.")

    text = gemini.generate(COPILOT_SYSTEM, prompt, temperature=0.35,
                           max_output_tokens=1400)

    now = datetime.now(timezone.utc)
    grounding = {"facts": context["facts"],
                 "station": context["station"], "city": context["city"]}

    if conversation is not None:
        conversation.messages.append(
            Message(role="user", content=clean_question, at=now))
        conversation.messages.append(
            Message(role="assistant", content=text, at=now, grounding=grounding))
        if conversation.title == "New conversation":
            conversation.title = clean_question[:120]
        db.commit()

    return {"answer": text, "grounding": grounding, "generated_at": now,
            "model": "gemini", "kind": "ai_generated"}
