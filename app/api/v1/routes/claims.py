from __future__ import annotations

from collections import Counter
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

api_router = APIRouter()

RiskLevel = Literal["High", "Medium", "Low"]
Region = Literal["NSW", "QLD", "VIC", "WA"]
StatusDot = Literal["primary", "tertiary", "zinc"]

CLAIM_TYPES = ["Prime Mover", "Articulated", "Box Truck", "Reefer", "Heavy Rigid"]


def build_claims() -> list[dict[str, object]]:
    claims: list[dict[str, object]] = [
        {
            "id": "CL-8842-X",
            "lodged": "12 Oct 2023",
            "type": "Prime Mover",
            "region": "QLD",
            "statusDot": "primary",
            "risk": "High",
            "complexity": 92,
            "action": "Assign Senior",
            "confidencePct": 93,
        },
        {
            "id": "CL-8901-A",
            "lodged": "14 Oct 2023",
            "type": "Articulated",
            "region": "QLD",
            "statusDot": "tertiary",
            "risk": "Medium",
            "complexity": 68,
            "action": "Investigate",
            "confidencePct": 87,
        },
        {
            "id": "CL-8923-B",
            "lodged": "15 Oct 2023",
            "type": "Box Truck",
            "region": "NSW",
            "statusDot": "zinc",
            "risk": "Low",
            "complexity": 24,
            "action": "Fast Track",
            "confidencePct": 61,
        },
        {
            "id": "CL-8944-M",
            "lodged": "15 Oct 2023",
            "type": "Prime Mover",
            "region": "VIC",
            "statusDot": "primary",
            "risk": "High",
            "complexity": 88,
            "action": "Assign Senior",
            "confidencePct": 81,
        },
        {
            "id": "CL-8955-L",
            "lodged": "16 Oct 2023",
            "type": "Reefer",
            "region": "WA",
            "statusDot": "tertiary",
            "risk": "Medium",
            "complexity": 54,
            "action": "Investigate",
            "confidencePct": 74,
        },
    ]

    regions: list[Region] = ["NSW", "QLD", "VIC", "WA"]
    risks: list[RiskLevel] = ["High", "Medium", "Low"]
    dots: list[StatusDot] = ["primary", "tertiary", "zinc"]

    for i in range(31):
        n = 9000 + i + 10
        suffix = chr(65 + (i % 26))
        risk = risks[i % len(risks)]
        claim_type = CLAIM_TYPES[(i + 2) % len(CLAIM_TYPES)]
        region = regions[(i + 1) % len(regions)]

        if risk == "High":
            complexity = 70 + (i * 7) % 30
            confidence_pct = 78 + (i % 18)
            action = "Assign Senior"
        elif risk == "Medium":
            complexity = 40 + (i * 9) % 35
            confidence_pct = 60 + (i % 28)
            action = "Investigate"
        else:
            complexity = 10 + (i * 11) % 30
            confidence_pct = 40 + (i % 30)
            action = "Fast Track"

        day = 1 + (i % 27)
        month = ["Oct", "Nov", "Dec"][(i + 1) % 3]

        claims.append(
            {
                "id": f"CL-{n}-{suffix}",
                "lodged": f"{day} {month} 2023",
                "type": claim_type,
                "region": region,
                "statusDot": dots[i % len(dots)],
                "risk": risk,
                "complexity": complexity,
                "action": action,
                "confidencePct": confidence_pct,
            }
        )

    return sorted(claims, key=lambda claim: int(claim["complexity"]), reverse=True)


CLAIMS = build_claims()


def normalize_tokens(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    return {value.strip().lower() for value in values if value.strip()}


def claim_matches(
    claim: dict[str, object],
    search: str | None,
    risks: set[str] | None,
    claim_type: str | None,
    region: str | None,
) -> bool:
    if risks is not None and str(claim["risk"]).lower() not in risks:
        return False
    if claim_type and claim_type != "All Types" and claim["type"] != claim_type:
        return False
    if region and claim["region"] != region:
        return False

    if search:
        search_value = search.strip().lower()
        haystack = " ".join(
            [
                str(claim["id"]),
                str(claim["lodged"]),
                str(claim["type"]),
                str(claim["region"]),
                str(claim["risk"]),
                str(claim["action"]),
            ]
        ).lower()
        if search_value not in haystack:
            return False

    return True


@api_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@api_router.get("/claims")
async def list_claims(
    search: str | None = None,
    risk: Annotated[list[str] | None, Query()] = None,
    claim_type: str | None = Query(default=None, alias="type"),
    region: Region | None = None,
    page: int = 1,
    page_size: int = 12,
) -> dict[str, object]:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be greater than or equal to 1")
    if page_size < 1:
        raise HTTPException(status_code=400, detail="page_size must be greater than or equal to 1")

    risk_filter = normalize_tokens(risk)
    filtered = [
        claim
        for claim in CLAIMS
        if claim_matches(claim, search, risk_filter, claim_type, region)
    ]

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * page_size
    end = start + page_size

    return {
        "items": filtered[start:end],
        "page": safe_page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "filters": {
            "search": search,
            "risk": risk,
            "type": claim_type,
            "region": region,
        },
    }


def build_summary() -> dict[str, object]:
    risk_counts = Counter(str(claim["risk"]) for claim in CLAIMS)
    total_complexity = sum(int(claim["complexity"]) for claim in CLAIMS)
    avg_complexity = round(total_complexity / len(CLAIMS), 1) if CLAIMS else 0.0

    return {
        "total_active": len(CLAIMS),
        "risk_counts": {
            "High": risk_counts.get("High", 0),
            "Medium": risk_counts.get("Medium", 0),
            "Low": risk_counts.get("Low", 0),
        },
        "avg_complexity": avg_complexity,
        "intervention": sum(1 for claim in CLAIMS if claim["risk"] == "High"),
        "claim_types": CLAIM_TYPES,
        "regions": ["NSW", "QLD", "VIC", "WA"],
    }


@api_router.get("/claims/summary")
async def claims_summary() -> dict[str, object]:
    return build_summary()


@api_router.get("/dashboard/summary")
async def dashboard_summary() -> dict[str, object]:
    return build_summary()


@api_router.get("/claims/{claim_id}")
async def get_claim(claim_id: str) -> dict[str, object]:
    for claim in CLAIMS:
        if claim["id"] == claim_id:
            return claim
    raise HTTPException(status_code=404, detail="Claim not found")