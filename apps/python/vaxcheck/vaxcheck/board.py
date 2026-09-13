"""Immunisation-day board: the roster as a single self-contained HTML page.

The text report is for a terminal; this is for the school nurse's laptop at
7 a.m. Same data, same rules, same ordering: the review queue first, the settled
rows last, and the nurse's line at the bottom of every board.

No JavaScript, no external assets. Phone numbers arrive already masked.
"""

from __future__ import annotations

import html
import json
from typing import Any

from .triage import CLEARED, DECLINED, NURSE_REVIEW, PRIVATE_PROVIDER, UNREACHABLE

_ORDER = [NURSE_REVIEW, UNREACHABLE, PRIVATE_PROVIDER, DECLINED, CLEARED]
_LABEL = {
    NURSE_REVIEW: "Nurse review required",
    UNREACHABLE: "Not reached · retry",
    PRIVATE_PROVIDER: "Own doctor · do not vaccinate",
    DECLINED: "Declined · do not vaccinate",
    CLEARED: "Cleared for session",
}
_TONE = {
    NURSE_REVIEW: "review",
    UNREACHABLE: "retry",
    PRIVATE_PROVIDER: "settled",
    DECLINED: "settled",
    CLEARED: "clear",
}
_FIELD_LABEL = {
    "consent": "Consent",
    "route": "Route",
    "allergy_reported": "Allergy",
    "allergy_detail": "Allergy detail",
    "prior_dose_reported": "Prior dose",
    "prior_dose_detail": "Prior dose detail",
    "unwell_today": "Unwell today",
    "guardian_questions": "Guardian asked",
    "callback_requested": "Callback requested",
    "identity_confirmed": "Identity confirmed",
    "reached_guardian": "Reached",
}

CSS = """
:root{--paper:#FAF7EF;--paper2:#EFE9DC;--ink:#243F50;--ink2:#3D5566;--teal:#648E8D;--teal2:#3F6B6A;--amber:#B58B37;--grey:#8A8F96;--line:#D9D2C2}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.45 "Source Serif 4",Georgia,serif}
.wrap{max-width:1180px;margin:0 auto;padding:40px 32px 64px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding-bottom:20px;border-bottom:3px solid var(--teal)}
.brand{font-family:"Jost","Avenir Next",system-ui,sans-serif;font-weight:500;font-size:30px;letter-spacing:-.01em}
.session h1{font-size:34px;margin:0 0 4px;letter-spacing:-.02em;font-weight:600}
.session .meta{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:14px;color:var(--ink2)}
.counts{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:26px 0 34px}
.count{background:#fff;border:2px solid var(--line);border-radius:10px;padding:14px 16px}
.count b{display:block;font-size:40px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.count span{display:block;margin-top:6px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--ink2);text-transform:uppercase;letter-spacing:.06em}
.count.review{border-color:var(--amber)} .count.review b{color:var(--amber)}
.count.clear{border-color:var(--teal)} .count.clear b{color:var(--teal2)}
section{margin-top:30px}
h2{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin:0 0 12px;display:flex;align-items:center;gap:10px}
h2 .n{background:var(--paper2);border-radius:999px;padding:2px 10px;color:var(--ink)}
.card{background:#fff;border:2px solid var(--line);border-radius:12px;padding:16px 20px;margin-bottom:12px;display:grid;grid-template-columns:1fr 1.4fr;gap:8px 28px;position:relative}
.card.review{border-left:8px solid var(--amber)}
.card.clear{border-left:8px solid var(--teal)}
.card.retry{border-left:8px solid var(--grey)}
.card.settled{border-left:8px solid var(--line)}
.who{font-size:22px;font-weight:600;letter-spacing:-.01em}
.who small{display:block;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:13px;color:var(--ink2);font-weight:400;margin-top:4px}
.reasons{margin:0;padding:0;list-style:none}
.reasons li{padding-left:18px;position:relative;margin:2px 0}
.reasons li::before{content:"";position:absolute;left:0;top:.6em;width:8px;height:8px;border-radius:50%;background:var(--amber)}
.card.clear .reasons li::before,.card.settled .reasons li::before,.card.retry .reasons li::before{background:var(--grey)}
.reported{grid-column:1/-1;border-top:1px dashed var(--line);padding-top:10px;margin-top:4px;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px 18px;font-size:15px}
.reported div{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:13px;color:var(--ink2)}
.reported div b{display:block;font-family:"Source Serif 4",Georgia,serif;font-size:16px;color:var(--ink);font-weight:600}
.reported div.flag b{color:var(--amber)}
.conf{position:absolute;right:20px;top:16px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--ink2)}
.checks{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.check{background:#fff;border:2px solid var(--line);border-radius:10px;padding:12px 16px;display:grid;grid-template-columns:76px 1fr;gap:12px;align-items:center}
.check b{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:13px;letter-spacing:.08em;padding:4px 0;text-align:center;border-radius:6px;background:var(--paper2)}
.check.pass b{background:#DDEBE5;color:#2F6B57}.check.warn b{background:#F3E7C8;color:#7A5A12}.check.fail b{background:#F1D9D3;color:#8A3A2B}
.check span{font-size:15px}.check span small{display:block;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12px;color:var(--ink2);margin-top:2px}
.pf{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.pf div{background:#fff;border:2px solid var(--line);border-radius:10px;padding:10px 14px;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:14px;display:flex;justify-content:space-between}
.pf .ok{color:#2F6B57;font-weight:600}.pf .blocked{color:#8A3A2B;font-weight:600}
footer{margin-top:40px;padding-top:18px;border-top:3px solid var(--ink);font-size:18px;font-style:italic;color:var(--ink2)}
"""


def _esc(v: Any) -> str:
    return html.escape("" if v is None else str(v))


def _reported(result: dict[str, Any]) -> str:
    cells = []
    for key in ("consent", "route", "allergy_reported", "unwell_today", "prior_dose_reported",
                "callback_requested", "guardian_questions", "allergy_detail", "prior_dose_detail"):
        val = result.get(key)
        if val in (None, ""):
            continue
        flag = (key == "allergy_reported" and val in ("severe", "unsure")) or \
               (key == "unwell_today" and val in ("yes", "unsure")) or \
               (key == "prior_dose_reported" and val in ("yes", "unsure")) or \
               (key == "guardian_questions") or (key == "callback_requested" and val == "yes")
        cells.append(f'<div class="{"flag" if flag else ""}">{_esc(_FIELD_LABEL.get(key, key))}<b>{_esc(str(val).replace("_", " "))}</b></div>')
    return f'<div class="reported">{"".join(cells)}</div>' if cells else ""


def _card(s: dict[str, Any]) -> str:
    tone = _TONE.get(s["disposition"], "settled")
    reasons = "".join(f"<li>{_esc(r)}</li>" for r in s.get("reasons", []))
    conf = s.get("completion_confidence")
    conf_html = f'<div class="conf">confidence {conf:.2f}</div>' if isinstance(conf, (int, float)) else ""
    return (
        f'<div class="card {tone}" id="card-{_esc(s["student_id"])}">{conf_html}'
        f'<div class="who">{_esc(s["student_name"])}<small>{_esc(s["class_name"])} · {_esc(s["student_id"])} · guardian {_esc(s["guardian_phone"])}</small></div>'
        f'<ul class="reasons">{reasons}</ul>'
        f'{_reported(s.get("result") or {})}'
        f"</div>"
    )


def render(roster: dict[str, Any], doctor: list[dict[str, Any]] | None = None,
           preflight: list[dict[str, Any]] | None = None) -> str:
    """Render the board from the JSON the CLI writes with --out."""
    sess = roster["session"]
    students = roster["students"]
    counts = roster.get("counts", {})
    by = {d: [s for s in students if s["disposition"] == d] for d in _ORDER}

    count_tiles = "".join(
        f'<div class="count {_TONE[d]}"><b>{len(by[d])}</b><span>{_esc(_LABEL[d])}</span></div>' for d in _ORDER
    )
    sections = []
    for d in _ORDER:
        if not by[d]:
            continue
        sections.append(f'<section><h2>{_esc(_LABEL[d])} <span class="n">{len(by[d])}</span></h2>{"".join(_card(s) for s in by[d])}</section>')

    live = ""
    if doctor:
        checks = "".join(
            f'<div class="check {c["status"]}"><b>{_esc(c["status"]).upper()}</b><span>{_esc(c["name"])}<small>{_esc(c["detail"])}</small></span></div>'
            for c in doctor
        )
        live += f'<section id="sec-readiness"><h2>Readiness · live CALL-E checks</h2><div class="checks">{checks}</div></section>'
    if preflight:
        rows = "".join(
            f'<div><span>{_esc(p["student_id"])} · {_esc(p["guardian_phone"])}</span><span class="{"ok" if p["ready_to_run"] else "blocked"}">{"ready" if p["ready_to_run"] else "blocked"}</span></div>'
            for p in preflight
        )
        ready = sum(1 for p in preflight if p["ready_to_run"])
        live += f'<section id="sec-preflight"><h2>Preflight · plan_call per student <span class="n">{ready}/{len(preflight)} ready</span></h2><div class="pf">{rows}</div></section>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>VaxCheck · {_esc(sess["school_name"])} · {_esc(sess["session_date"])}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head>
<body><div class="wrap">
<header id="board-header"><div class="session"><h1>{_esc(sess["school_name"])}</h1><div class="meta">{_esc(sess["vaccine_name"])} · session {_esc(sess["session_date"])} · {_esc(sess["region"])}/{_esc(sess["language"])} · {len(students)} students</div></div><div class="brand">VaxCheck</div></header>
<div class="counts" id="counts">{count_tiles}</div>
{live}
{"".join(sections)}
<footer id="board-footer">No student is vaccinated on this board alone. A nurse confirms the final list, and every review row must be resolved by a person first.</footer>
</div></body></html>"""


def render_file(roster_path: str, out_path: str, doctor_path: str | None = None,
                preflight_path: str | None = None) -> None:
    roster = json.load(open(roster_path, encoding="utf-8"))
    doctor = json.load(open(doctor_path, encoding="utf-8")) if doctor_path else None
    preflight = json.load(open(preflight_path, encoding="utf-8")) if preflight_path else None
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render(roster, doctor, preflight))
