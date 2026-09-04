from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import copilot as copilot_service
from app.ai import gemini
from app.api.deps import get_current_user_optional
from app.api.v1.common import ensure_fresh, resolve_city, resolve_station
from app.api.v1.sources import estimate_for_station
from app.core.errors import InvalidRequest
from app.db.models import Conversation, User
from app.db.session import get_db
from app.schemas.action import CopilotRequest, CopilotResponse
from app.schemas.common import DataKind, DataProvenance, SourceMode
from ml.predict import forecast_station

router = APIRouter(prefix="/copilot", tags=["AI copilot"])


@router.get("/suggestions")
def suggestions() -> dict:
    return {"available": gemini.available(),
            "questions": copilot_service.SUGGESTED_QUESTIONS}


@router.post("", response_model=CopilotResponse)
def ask(payload: CopilotRequest, db: Session = Depends(get_db),
        user: User | None = Depends(get_current_user_optional)) -> CopilotResponse:
    city = resolve_city(db, payload.city_slug)
    station = resolve_station(db, city, payload.station_id)
    ensure_fresh(db, city, station)

    conversation: Conversation | None = None
    if payload.conversation_id is not None:
        conversation = db.get(Conversation, payload.conversation_id)
        if conversation is None:
            raise InvalidRequest("Unknown conversation.")
        if conversation.user_id is not None and (user is None or conversation.user_id != user.id):
            raise InvalidRequest("Unknown conversation.")
    elif user is not None:
        conversation = Conversation(user_id=user.id, city_id=city.id)
        db.add(conversation)
        db.flush()

    horizons, _ = forecast_station(db, station, horizons=(6, 24))
    estimate, _, _ = estimate_for_station(db, station)

    result = copilot_service.answer(
        db, question=payload.question, city=city, station=station,
        forecasts=horizons, source_estimate=estimate,
        conversation=conversation, user=user)

    return CopilotResponse(
        answer=result["answer"], grounding=result["grounding"],
        conversation_id=conversation.id if conversation else None,
        generated_at=result["generated_at"],
        suggested_questions=copilot_service.SUGGESTED_QUESTIONS,
        provenance=DataProvenance(
            kind=DataKind.ai_generated, mode=SourceMode.live,
            source="Gemini, grounded on AIRS data",
            generated_at=datetime.now(timezone.utc),
            note="AI-generated explanation based only on the AIRS data shown in "
                 "the grounding panel. Figures are not produced by the language "
                 "model."))


@router.get("/conversations")
def conversations(db: Session = Depends(get_db),
                  user: User | None = Depends(get_current_user_optional)) -> list[dict]:
    if user is None:
        return []
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id)
                      .order_by(Conversation.updated_at.desc()).limit(30))
    return [{"id": c.id, "title": c.title, "updated_at": c.updated_at,
             "message_count": len(c.messages)} for c in rows]


@router.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id: int, db: Session = Depends(get_db),
                        user: User | None = Depends(get_current_user_optional)) -> dict:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or (conversation.user_id is not None
                                and (user is None or conversation.user_id != user.id)):
        raise InvalidRequest("Unknown conversation.")
    return {"id": conversation.id, "title": conversation.title,
            "messages": [{"role": m.role, "content": m.content, "at": m.at,
                          "grounding": m.grounding} for m in conversation.messages]}
