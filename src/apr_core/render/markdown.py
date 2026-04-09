from __future__ import annotations

SCIENTIFIC_RECORD_ORDER = (
    "problem_definition_and_claim_clarity",
    "structural_integrity",
    "methodological_legibility",
    "evidence_to_claim_alignment",
    "claim_evidence_calibration",
    "literature_positioning",
    "transparency_and_reporting_readiness",
    "integrity_and_policy_readiness",
    "adversarial_resilience",
)


def _bullet_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def render_markdown_report(record: dict[str, object]) -> str:
    lines = [
        "# APR v2 Audit Summary",
        "",
        f"**Recommendation:** {record['decision']['recommendation']}",
        f"**Confidence:** {record['decision']['confidence']}",
        f"**Human escalation required:** {record['decision']['human_escalation_required']}",
        f"**Editorial forecast:** {record['decision']['editorial_forecast']}",
        f"**Author recommendation:** {record['decision']['author_recommendation']}",
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

    lines.extend(["", "## Transparency"])
    lines.append(f"- Status: {record['transparency']['status']}")
    lines.extend(_bullet_list(record["transparency"]["missing_items"]))

    lines.extend(["", "## Integrity"])
    lines.append(f"- Status: {record['integrity']['status']}")
    lines.extend(_bullet_list(record["integrity"]["flags"]))

    lines.extend(["", "## Structural integrity"])
    lines.append(f"- Status: {record['structural_integrity']['status']}")
    lines.append(f"- Research spine score: {record['structural_integrity']['research_spine_score_8']}/8")
    lines.extend(_bullet_list(record["structural_integrity"]["missing_elements"]))

    lines.extend(["", "## Claim-evidence calibration"])
    lines.append(f"- Status: {record['claim_evidence_calibration']['status']}")
    lines.append(f"- Claim magnitude: {record['claim_evidence_calibration']['claim_magnitude']}")
    lines.append(f"- Evidence level: {record['claim_evidence_calibration']['evidence_level']}")
    lines.append(f"- Mismatch: {record['claim_evidence_calibration']['mismatch']}")

    lines.extend(["", "## Adversarial resilience"])
    lines.append(f"- Status: {record['adversarial_resilience']['status']}")
    lines.append(f"- Flag count: {record['adversarial_resilience']['flag_count']}")
    lines.extend(_bullet_list(record["adversarial_resilience"]["flags"]))

    lines.extend(["", "## Scientific record"])
    lines.append(f"- Status: {record['scientific_record']['status']}")
    for criterion_name in SCIENTIFIC_RECORD_ORDER:
        detail = record["scientific_record"]["criteria"][criterion_name]
        lines.append(f"- {criterion_name}: {detail['status']} ({detail['severity']})")
        lines.append(f"  Why: {detail['why']}")

    lines.extend(["", "## Venue routing"])
    lines.append(f"- Routing state: {record['venue']['routing_state']}")
    lines.extend(_bullet_list(record["venue"]["rationale"]))

    lines.extend(["", "## Editorial first pass"])
    lines.append(f"- Score: {record['editorial_first_pass']['editorial_first_pass_score_32']}/32")
    lines.append(f"- Desk reject probability: {record['editorial_first_pass']['desk_reject_probability']}")
    for name, score in record["editorial_first_pass"]["component_scores"].items():
        lines.append(f"- {name}: {score}")

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
