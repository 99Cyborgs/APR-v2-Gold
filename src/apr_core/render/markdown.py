from __future__ import annotations

from typing import Any


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def render_markdown_report(record: dict[str, Any]) -> str:
    lines = [
        "# APR v2 Audit Summary",
        "",
        f"**Recommendation:** {record['decision']['recommendation']}",
        f"**Confidence:** {record['decision']['confidence']}",
        f"**Human escalation required:** {record['decision']['human_escalation_required']}",
        "",
        "## Central claim",
        record["parsing"]["central_claim"] or "No recoverable central claim.",
        "",
        "## Classification",
        f"- Article type: {record['classification']['article_type']}",
        f"- Claim type: {record['classification']['claim_type']}",
        f"- Domain module: {record['classification']['domain_module']}",
        f"- Outlet profile: {record['classification']['outlet_profile']}",
        "",
        "## Reviewability",
        f"- Status: {record['reviewability']['status']}",
    ]
    for name, status in record["reviewability"]["checks"].items():
        lines.append(f"- {name}: {status}")
    lines.extend(["", "## Scientific record"])
    lines.append(f"- Status: {record['scientific_record']['status']}")
    for criterion_name, detail in record["scientific_record"]["criteria"].items():
        lines.append(f"- {criterion_name}: {detail['status']} ({detail['severity']})")
        lines.append(f"  Why: {detail['why']}")
    lines.extend(["", "## Venue routing"])
    lines.append(f"- Routing state: {record['venue']['routing_state']}")
    lines.extend(_bullet_list(record["venue"]["rationale"]))
    lines.extend(["", "## Rehabilitation"])
    lines.append(f"- Development track: {record['rehabilitation']['development_track']}")
    lines.append(f"- One publishable unit: {record['rehabilitation']['one_publishable_unit']}")
    lines.extend(_bullet_list(record["rehabilitation"]["next_actions_ranked"]))
    lines.extend(["", "## Packs"])
    if record["pack_results"]:
        for result in record["pack_results"]:
            lines.append(f"- {result['display_name']} ({result['status']}, {result['applicability']})")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
