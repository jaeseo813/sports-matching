from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.sport import SportOut
from app.sports.registry import SPORTS, faq_of

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("", response_model=list[SportOut])
async def list_sports(_: CurrentUser) -> list[SportOut]:
    return [
        SportOut(
            id=r.id,
            name=r.name,
            team_count=r.team_count,
            players_per_team=list(r.players_per_team),
            positions=list(r.positions),
            tier_labels=dict(r.tier_labels),
            faq=[q for q, _ in faq_of(r.id)],
        )
        for r in SPORTS.values()
    ]
