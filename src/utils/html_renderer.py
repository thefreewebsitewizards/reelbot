"""HTML rendering for plan views.

Converts PipelineResult into a standalone HTML page using the plan_view.html template.
"""
import json
import re
from pathlib import Path

from src.models import ContentComparison, PipelineResult


def render_plan_html(result: PipelineResult) -> str:
    """Render the full plan as a standalone HTML page."""
    template_path = Path(__file__).resolve().parent.parent.parent / "static" / "plan_view.html"
    if not template_path.exists():
        return "<html><body><p>Template not found</p></body></html>"

    template = template_path.read_text()
    analysis = result.analysis
    plan = result.plan
    score = analysis.relevance_score

    replacements = {
        "{{recommended_action_html}}": _build_recommended_action_html(plan),
        "{{similarity_html}}": _build_similarity_html(result),
        "{{comparison_html}}": _build_comparison_html(result),
        "{{social_media_html}}": _build_social_media_html(result.analysis),
        "{{title}}": html_esc(plan.title),
        "{{theme}}": html_esc(analysis.theme) if analysis.theme else "",
        "{{relevance_score}}": f"{score:.0%}",
        "{{relevance_color}}": "#22c55e" if score >= 0.85 else "#f59e0b" if score >= 0.70 else "#ef4444",
        "{{business_impact}}": html_esc(analysis.business_impact) if analysis.business_impact else "",
        "{{summary}}": md_to_html(plan.summary),
        "{{video_breakdown_html}}": _build_video_breakdown_html(analysis),
        "{{notes_html}}": _build_notes_html(analysis),
        "{{applications_html}}": _build_applications_html(analysis),
        "{{insights_html}}": "".join(f"<li>{md_to_html(i)}</li>" for i in analysis.key_insights),
        "{{fact_checks_section}}": _build_reality_checks_section(analysis),
        "{{tasks_json}}": _build_tasks_json(plan),
        "{{duration}}": f"{int(result.metadata.duration)}s" if result.metadata.duration < 60 else f"{int(result.metadata.duration // 60)}m {int(result.metadata.duration % 60)}s",
        "{{level_summaries_html}}": _build_level_summaries_html(plan),
        "{{source_url}}": html_esc(result.metadata.url),
        "{{creator}}": html_esc(result.metadata.creator),
        "{{category}}": html_esc(analysis.category),
        "{{routed_to_html}}": f' &middot; <span class="badge badge-route">{html_esc(analysis.routing_target)}</span>' if analysis.routing_target else "",
        "{{cost_html}}": _build_cost_table(result),
        "{{reel_id}}": html_esc(result.reel_id),
        "{{status}}": result.status.value,
    }

    html = template
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def html_esc(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def md_to_html(text: str) -> str:
    """Convert basic markdown to HTML (bold, italic, code, line breaks, bullets)."""
    if not text:
        return ""
    escaped = html_esc(text)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'(?<!</strong>)\*(.+?)\*', r'<em>\1</em>', escaped)
    escaped = re.sub(r'`(.+?)`', r'<code>\1</code>', escaped)

    lines = escaped.split('\n')
    result_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            result_lines.append(f'<li>{stripped[2:]}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(f'{stripped}<br>' if stripped else '<br>')
    if in_list:
        result_lines.append('</ul>')

    html = '\n'.join(result_lines)
    html = html.replace('<br>\n<ul>', '\n<ul>')
    if html.endswith('<br>'):
        html = html[:-4]
    return html


def _build_similarity_html(result: PipelineResult) -> str:
    if not result.similarity or not result.similarity.similar_plans:
        return ""
    top = result.similarity.similar_plans[0]
    rec_text = {
        "merge": "Consider merging tasks rather than separate execution.",
        "skip": "Very similar -- review carefully before proceeding.",
        "generate": "Different enough to proceed.",
    }.get(result.similarity.recommendation, "")
    html = (
        f'<div class="similarity-callout">'
        f'<strong>Similar to:</strong> {html_esc(top.title)} ({top.score}% overlap)'
    )
    if top.overlap_areas:
        html += f'<br>Overlap: {html_esc(", ".join(top.overlap_areas))}'
    if rec_text:
        html += f'<br><em>{rec_text}</em>'
    html += '</div>'
    return html


def _build_applications_html(analysis) -> str:
    if not analysis.business_applications:
        return ""
    html = ""
    for ba in analysis.business_applications:
        color = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}.get(ba.urgency, "#94a3b8")
        html += (
            f'<div class="card" style="border-left: 3px solid {color};">'
            f'<span class="badge" style="background:{color};">{ba.urgency.upper()}</span> '
            f'<strong>{html_esc(ba.area)}</strong> <em>({html_esc(ba.target_system)})</em>'
            f'<p>{md_to_html(ba.recommendation)}</p></div>'
        )
    return html


def _build_reality_checks_section(analysis) -> str:
    if not analysis.reality_checks:
        return ""
    html = ""
    verdict_icons = {
        "solid": "\u2705", "plausible": "\U0001F914",
        "questionable": "\u26A0\uFE0F", "misleading": "\u274C",
    }
    for rc in analysis.reality_checks:
        icon = verdict_icons.get(rc.verdict, "\U0001F914")
        verdict_label = rc.verdict.upper()
        rc_line = (
            f'<div class="card"><strong>{icon} [{verdict_label}]</strong> '
            f'"{html_esc(rc.claim)}" &mdash; {html_esc(rc.explanation)}'
        )
        if rc.better_alternative:
            rc_line += f"<br><em>Instead: {html_esc(rc.better_alternative)}</em>"
        rc_line += "</div>"
        html += rc_line
    return f'<h2>Reality Check</h2>\n<div>{html}</div>'


def _build_recommended_action_html(plan) -> str:
    if not plan.recommended_action:
        return ""
    return (
        f'<div class="impact" style="border-left-color:#22c55e;">'
        f'<strong>Do this:</strong> {html_esc(plan.recommended_action)}'
        f'</div>'
    )


def _build_level_summaries_html(plan) -> str:
    if not plan.level_summaries:
        return ""
    level_labels = {"1": "L1 -- Note it", "2": "L2 -- Build it", "3": "L3 -- Go deep"}
    items = "".join(
        f'<li><strong>{level_labels.get(k, f"L{k}")}:</strong> {html_esc(v)}</li>'
        for k, v in plan.level_summaries.items()
    )
    return f'<h2>Implementation Levels</h2><ul>{items}</ul>'


def _build_tasks_json(plan) -> str:
    return json.dumps([{
        "title": t.title, "description": t.description, "priority": t.priority,
        "estimated_hours": t.estimated_hours, "tools": t.tools,
        "deliverables": t.deliverables, "level": t.level,
        "requires_human": t.requires_human, "human_reason": t.human_reason or "",
        "change_type": t.change_type,
    } for t in plan.tasks])


def _build_video_breakdown_html(analysis) -> str:
    vb = analysis.video_breakdown
    if not vb.main_points and not vb.key_quotes:
        return ""
    html = ''
    if vb.creator_context:
        html += f'<div class="creator-ctx">{html_esc(vb.creator_context)}</div>'
    if vb.hook:
        html += f'<div class="hook"><strong>Hook:</strong> {html_esc(vb.hook)}</div>'
    if vb.main_points:
        points = "".join(f"<li>{html_esc(p)}</li>" for p in vb.main_points)
        html += f'<ul class="point-list">{points}</ul>'
    if vb.key_quotes:
        for q in vb.key_quotes:
            html += f'<div class="quote">&ldquo;{html_esc(q)}&rdquo;</div>'
    return html


def _build_notes_html(analysis) -> str:
    notes = analysis.detailed_notes
    if not notes.what_it_is and not notes.how_useful:
        return ""
    html = ""
    if notes.what_it_is:
        html += f"<p><strong>What it is:</strong> {md_to_html(notes.what_it_is)}</p>"
    if notes.how_useful:
        html += f"<p><strong>How it helps us:</strong> {md_to_html(notes.how_useful)}</p>"
    if notes.how_not_useful:
        html += f"<p><strong>Limitations:</strong> {md_to_html(notes.how_not_useful)}</p>"
    if notes.target_audience:
        html += f"<p><strong>Who should see this:</strong> {html_esc(notes.target_audience)}</p>"
    return html


def _build_comparison_html(result: PipelineResult) -> str:
    """Build comparison cards from similarity comparisons."""
    if not result.similarity or not result.similarity.similar_plans:
        return ""
    comparisons: list[tuple[str, ContentComparison]] = []
    for sp in result.similarity.similar_plans:
        for c in sp.comparisons:
            comparisons.append((sp.title, c))
    if not comparisons:
        return ""
    verdict_colors = {
        "better": "#22c55e",
        "worse": "#ef4444",
        "same": "#94a3b8",
        "different_angle": "#60a5fa",
    }
    html = '<h2>Comparison to Current State</h2>'
    for _plan_title, c in comparisons:
        color = verdict_colors.get(c.verdict, "#94a3b8")
        badge = c.verdict.replace("_", " ").upper()
        html += (
            f'<div class="card" style="border-left: 3px solid {color};">'
            f'<strong>{html_esc(c.area)}</strong> '
            f'<span class="badge" style="background:{color};">{badge}</span>'
            f'<p><strong>Current:</strong> {html_esc(c.current_content)}</p>'
            f'<p><strong>New:</strong> {html_esc(c.new_content)}</p>'
            f'<p><em>{html_esc(c.explanation)}</em></p>'
            f'</div>'
        )
    return html


def _build_social_media_html(analysis) -> str:
    """Build social media play section from content_response."""
    cr = analysis.content_response
    if not cr.react_angle and not cr.corrections and not cr.repurpose_ideas and not cr.engagement_hook:
        return ""
    html = '<h2 id="section-social">Social Media Play</h2>'
    if cr.react_angle:
        html += (
            f'<div class="card">'
            f'<strong>React Angle</strong>'
            f'<p>{html_esc(cr.react_angle)}</p>'
            f'</div>'
        )
    if cr.corrections:
        items = "".join(f"<li>{html_esc(c)}</li>" for c in cr.corrections)
        html += (
            f'<div class="card">'
            f'<strong>Corrections</strong>'
            f'<ul>{items}</ul>'
            f'</div>'
        )
    if cr.repurpose_ideas:
        items = "".join(f"<li>{html_esc(i)}</li>" for i in cr.repurpose_ideas)
        html += (
            f'<div class="card">'
            f'<strong>Repurpose Ideas</strong>'
            f'<ul>{items}</ul>'
            f'</div>'
        )
    if cr.engagement_hook:
        html += (
            f'<div class="card">'
            f'<strong>Engagement Hook</strong>'
            f'<p>{html_esc(cr.engagement_hook)}</p>'
            f'</div>'
        )
    return html


def _build_cost_table(result: PipelineResult) -> str:
    if not result.cost_breakdown or not result.cost_breakdown.calls:
        return ""
    cb = result.cost_breakdown
    cost_rows = "".join(
        f'<tr><td>{html_esc(c.step)}</td><td>{c.prompt_tokens:,}</td>'
        f'<td>{c.completion_tokens:,}</td><td>${c.cost_usd:.4f}</td></tr>'
        for c in cb.calls
    )
    return (
        f'<h2><a href="/costs" style="color:#f8fafc;text-decoration:none;">Cost Breakdown &#8594;</a></h2>'
        f'<div class="card"><div class="cost-table-wrap"><table>'
        f'<tr><th>Step</th><th>Prompt</th>'
        f'<th>Completion</th><th>Cost</th></tr>'
        f'{cost_rows}'
        f'<tr style="border-top:1px solid #475569;font-weight:600;">'
        f'<td style="color:#f1f5f9;">Total</td><td colspan="2"></td><td style="color:#f1f5f9;">${cb.total_cost_usd:.4f}</td></tr>'
        f'</table></div></div>'
    )
