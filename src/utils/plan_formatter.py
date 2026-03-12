"""Markdown formatting helpers for plan artifacts.

Formats analysis results and notes into markdown for plan files.
"""

from src.models import PipelineResult


def format_notes_md(result: PipelineResult) -> str:
    """Quick-reference analysis notes (no tasks)."""
    analysis = result.analysis
    lines = [
        f"# Analysis Notes: {result.metadata.creator}",
        "",
        f"**Source:** {result.metadata.url}",
        f"**Category:** {analysis.category}",
        f"**Relevance:** {analysis.relevance_score:.0%}",
    ]

    if analysis.theme:
        lines.extend(["", f"> *{analysis.theme}*"])

    if analysis.business_impact:
        lines.extend(["", f"**Bottom line:** {analysis.business_impact}"])

    lines.extend(["", "## Summary", "", analysis.summary])

    # Video breakdown
    vb = analysis.video_breakdown
    if vb.main_points or vb.key_quotes:
        lines.extend(["", "## What This Video Covers", ""])
        if vb.creator_context:
            lines.append(f"*{vb.creator_context}*")
            lines.append("")
        if vb.hook:
            lines.append(f"**Hook:** {vb.hook}")
            lines.append("")
        if vb.main_points:
            for i, point in enumerate(vb.main_points, 1):
                lines.append(f"{i}. {point}")
            lines.append("")
        if vb.key_quotes:
            lines.append("**Key quotes:**")
            for q in vb.key_quotes:
                lines.append(f'> "{q}"')
                lines.append("")

    notes = analysis.detailed_notes
    if notes.what_it_is:
        lines.extend(["", "## Notes", ""])
        if notes.what_it_is:
            lines.append(f"- **What:** {notes.what_it_is}")
        if notes.how_useful:
            lines.append(f"- **Useful:** {notes.how_useful}")
        if notes.how_not_useful:
            lines.append(f"- **Not useful:** {notes.how_not_useful}")
        if notes.target_audience:
            lines.append(f"- **For:** {notes.target_audience}")

    if analysis.business_applications:
        lines.extend(["", "## Applications", ""])
        for ba in analysis.business_applications:
            lines.append(f"- [{ba.urgency}] {ba.area} -> {ba.target_system}: {ba.recommendation}")

    lines.extend(["", "## Key Insights", ""])
    for insight in analysis.key_insights:
        lines.append(f"- {insight}")

    if analysis.swipe_phrases:
        lines.extend(["", "## Swipe Phrases", ""])
        for phrase in analysis.swipe_phrases:
            lines.append(f"- {phrase}")

    if analysis.fact_checks:
        lines.extend(["", "## Fact Checks", ""])
        for fc in analysis.fact_checks:
            lines.append(f"- [{fc.verdict}] {fc.claim}: {fc.explanation}")

    return "\n".join(lines)
