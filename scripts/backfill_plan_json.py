#!/usr/bin/env python3
"""One-time script to generate plan.json for existing plans that only have plan.md.
Parses the markdown to extract structured task data."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings


def parse_plan_md(text: str) -> dict:
    """Extract structured data from plan.md markdown."""
    lines = text.split("\n")
    title = ""
    summary = ""
    tasks = []
    current_task = None
    in_deliverables = False

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## Summary"):
            continue
        elif line.startswith("### ") and ". " in line:
            if current_task:
                tasks.append(current_task)
            task_text = line.lstrip("# ").strip()
            task_text = re.sub(r"^\d+\.\s*", "", task_text)
            requires_human = "[NEEDS HUMAN]" in task_text
            task_title = task_text.replace("[NEEDS HUMAN]", "").strip()
            current_task = {
                "title": task_title,
                "description": "",
                "priority": "medium",
                "estimated_hours": 1.0,
                "deliverables": [],
                "dependencies": [],
                "tools": [],
                "requires_human": requires_human,
                "human_reason": "",
            }
            in_deliverables = False
        elif current_task and line.startswith("**Priority:**"):
            match = re.search(r"Priority:\*\*\s*(\w+)", line)
            if match:
                current_task["priority"] = match.group(1)
            match = re.search(r"Hours:\*\*\s*([\d.]+)", line)
            if match:
                current_task["estimated_hours"] = float(match.group(1))
            match = re.search(r"Tools:\*\*\s*(.+)", line)
            if match:
                current_task["tools"] = [t.strip() for t in match.group(1).split(",")]
            in_deliverables = False
        elif current_task and line.startswith("**Why human needed:**"):
            current_task["human_reason"] = line.replace("**Why human needed:**", "").strip()
            in_deliverables = False
        elif current_task and line.startswith("**Deliverables:**"):
            in_deliverables = True
        elif current_task and in_deliverables and line.startswith("- "):
            current_task["deliverables"].append(line[2:].strip())
        elif current_task and not line.startswith("**") and not line.startswith("- ") and line.strip():
            if not current_task["description"]:
                current_task["description"] = line.strip()
            in_deliverables = False

    if current_task:
        tasks.append(current_task)

    return {
        "title": title,
        "summary": summary,
        "tasks": tasks,
        "total_estimated_hours": sum(t["estimated_hours"] for t in tasks),
    }


def main():
    plans_dir = settings.plans_dir
    count = 0
    for plan_dir in sorted(plans_dir.iterdir()):
        if not plan_dir.is_dir() or plan_dir.name.startswith("_"):
            continue
        plan_json = plan_dir / "plan.json"
        plan_md = plan_dir / "plan.md"
        if plan_json.exists():
            print(f"  skip {plan_dir.name} (already has plan.json)")
            continue
        if not plan_md.exists():
            continue
        data = parse_plan_md(plan_md.read_text())
        plan_json.write_text(json.dumps(data, indent=2))
        print(f"  created {plan_dir.name}/plan.json ({len(data['tasks'])} tasks)")
        count += 1

    print(f"\nBackfilled {count} plan(s)")


if __name__ == "__main__":
    main()
