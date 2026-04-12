from __future__ import annotations

from collections import defaultdict
from html import escape
import json
from pathlib import Path
from typing import Any

from apr_core.anchors import segment_payload
from apr_core.utils import write_text_bundle

_CATEGORY_CLASS = {
    "strength_anchor": "strength",
    "weakness_anchor": "weakness",
    "ambiguity_anchor": "ambiguity",
    "risk_anchor": "risk",
    "question_anchor": "question",
    "repair_anchor": "repair",
}


def _highlight_segment(text: str, annotations: list[dict[str, Any]]) -> str:
    escaped = escape(text)
    for annotation in annotations:
        quote = annotation.get("text_quote") or ""
        if len(quote) < 12:
            continue
        safe_quote = escape(quote)
        if safe_quote in escaped:
            css_class = _CATEGORY_CLASS.get(annotation["category"], "mark")
            escaped = escaped.replace(
                safe_quote,
                f'<span class="hl {css_class}">{safe_quote}</span>',
                1,
            )
    return escaped


def render_annotation_viewer_html(payload: dict[str, Any], manifest: dict[str, Any]) -> str:
    annotations_by_location: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for annotation in manifest.get("annotations", []):
        annotations_by_location[annotation.get("location", "fallback")].append(annotation)

    drilldowns = {item["drilldown_id"]: item for item in manifest.get("drilldowns", [])}
    segments = segment_payload(payload)

    segment_blocks: list[str] = []
    for segment in segments:
        annotations = annotations_by_location.get(segment["location"], [])
        badges = " ".join(
            f'<a class="badge {escape(_CATEGORY_CLASS.get(annotation["category"], "mark"))}" href="#{escape(annotation["drilldown_id"])}">{escape(annotation["short_inline_label"])}</a>'
            for annotation in annotations
        )
        segment_blocks.append(
            "\n".join(
                [
                    '<article class="segment">',
                    f'<div class="segment-meta">{escape(segment["location"])} {badges}</div>',
                    f'<p>{_highlight_segment(segment["quote"], annotations)}</p>',
                    "</article>",
                ]
            )
        )

    drilldown_blocks = []
    for drilldown in manifest.get("drilldowns", []):
        evidence = "".join(
            f"<li><strong>{escape(anchor['location'])}</strong>: {escape(anchor['quote'])}</li>"
            for anchor in drilldown.get("evidence", [])
        )
        risks = ", ".join(escape(item) for item in drilldown.get("linked_risk_items", [])) or "none"
        questions = ", ".join(escape(item) for item in drilldown.get("linked_question_items", [])) or "none"
        mitigations = "".join(f"<li>{escape(note)}</li>" for note in drilldown.get("mitigation_notes", []))
        drilldown_blocks.append(
            "\n".join(
                [
                    f'<section class="drilldown-card" id="{escape(drilldown["drilldown_id"])}">',
                    f"<h3>{escape(drilldown['title'])}</h3>",
                    f"<p>{escape(drilldown['summary'])}</p>",
                    f"<p><strong>Linked risks:</strong> {risks}</p>",
                    f"<p><strong>Linked questions:</strong> {questions}</p>",
                    f"<ul>{evidence or '<li>none</li>'}</ul>",
                    f"<ul>{mitigations or '<li>none</li>'}</ul>",
                    "</section>",
                ]
            )
        )

    source_pdf = manifest.get("source", {}).get("source_pdf_path")
    pdf_note = (
        f'<p class="pdf-note">Source PDF supplied: {escape(str(source_pdf))}</p>' if source_pdf else '<p class="pdf-note">Text-facsimile mode only. No PDF coordinate overlay was generated.</p>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(manifest.get("source", {}).get("title") or "APR Review Surface")}</title>
  <style>
    :root {{
      --paper: #fbf7ef;
      --ink: #1d1a16;
      --muted: #6e6257;
      --strength: #1b6b51;
      --weakness: #8b2d2d;
      --ambiguity: #9a6a12;
      --risk: #7a1f1f;
      --question: #154c79;
      --repair: #5f4b8b;
      --border: #d8cfc2;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f3efe7 0%, var(--paper) 100%);
      color: var(--ink);
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.9fr);
      gap: 24px;
      padding: 24px;
    }}
    .paper, .sidebar {{
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
      box-shadow: 0 18px 40px rgba(48, 37, 24, 0.08);
    }}
    .segment {{
      padding: 14px 0;
      border-top: 1px solid rgba(96, 80, 62, 0.14);
    }}
    .segment:first-child {{
      border-top: 0;
    }}
    .segment-meta {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    .badge {{
      display: inline-block;
      margin-left: 6px;
      padding: 2px 8px;
      border-radius: 999px;
      text-decoration: none;
      font-size: 0.8rem;
      color: white;
    }}
    .strength {{ background: var(--strength); }}
    .weakness {{ background: var(--weakness); }}
    .ambiguity {{ background: var(--ambiguity); }}
    .risk {{ background: var(--risk); }}
    .question {{ background: var(--question); }}
    .repair {{ background: var(--repair); }}
    .hl {{
      padding: 0 2px;
      border-radius: 4px;
      color: white;
    }}
    .hl.strength {{ background: color-mix(in srgb, var(--strength) 84%, white); }}
    .hl.weakness {{ background: color-mix(in srgb, var(--weakness) 84%, white); }}
    .hl.ambiguity {{ background: color-mix(in srgb, var(--ambiguity) 84%, white); }}
    .hl.risk {{ background: color-mix(in srgb, var(--risk) 84%, white); }}
    .hl.question {{ background: color-mix(in srgb, var(--question) 84%, white); }}
    .hl.repair {{ background: color-mix(in srgb, var(--repair) 84%, white); }}
    .drilldown-card {{
      border-top: 1px solid rgba(96, 80, 62, 0.14);
      padding: 16px 0;
    }}
    .drilldown-card:first-child {{
      border-top: 0;
    }}
    .pdf-note {{
      color: var(--muted);
      margin: 0 0 18px;
    }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <main class="paper">
      <h1>{escape(manifest.get("source", {}).get("title") or "APR Review Surface")}</h1>
      {pdf_note}
      {''.join(segment_blocks)}
    </main>
    <aside class="sidebar">
      <h2>Drilldowns</h2>
      {''.join(drilldown_blocks)}
    </aside>
  </div>
</body>
</html>
"""


def write_annotation_viewer(output_dir: str | Path, payload: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "annotation_manifest.json"
    html_path = output_path / "review.html"
    write_text_bundle(
        {
            manifest_path: json.dumps(manifest, indent=2) + "\n",
            html_path: render_annotation_viewer_html(payload, manifest),
        }
    )
    return {
        "manifest_path": str(manifest_path.resolve()),
        "html_path": str(html_path.resolve()),
    }
