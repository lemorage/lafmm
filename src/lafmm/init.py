import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

VERSION = "0.4.0"
LAFMM_DIR = ".lafmm"
HUMAN_DATA = "data"
AGENT_DATA = "cache"
SKILLS_SRC = "skills"
SKILLS_DST = ".claude/skills"

US_INDICES_GROUP = "us-indices"
US_INDICES_LEADERS = ("SPY", "QQQ")
US_INDICES_TRACKED = ("DIA", "IWM")
FALLBACK_SWING_PCT = 5.0
FALLBACK_CONFIRM_PCT = 2.5


def _lafmm_home() -> Path:
    return Path(os.environ.get("LAFMM_HOME", Path.home() / LAFMM_DIR))


def get_root() -> Path | None:
    root = _lafmm_home()
    return root if root.is_dir() else None


def scaffold() -> Path:
    root = _lafmm_home()
    if root.exists():
        return root

    root.mkdir()
    (root / HUMAN_DATA).mkdir()
    (root / AGENT_DATA).mkdir()
    (root / "AGENT.md").write_text(_agent_md())
    (root / "CLAUDE.md").write_text("@AGENT.md\n")
    (root / ".python").write_text(sys.executable)

    _scaffold_config(root)
    _scaffold_profile(root)
    _scaffold_insights(root)
    _scaffold_accounts(root)
    _configure_claude(root)
    _copy_skills(root)
    _scaffold_us_indices(root)
    _fetch_us_indices(root)
    _tune_us_indices(root)

    _write_version(root / ".version", None)
    return root


def _read_version(version_file: Path) -> str | None:
    if not version_file.exists():
        return None
    return version_file.read_text().split("\n", 1)[0].strip()


def _ver_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _parse_changelog() -> dict[str, list[str]]:
    changelog = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
    if not changelog.exists():
        return {}
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in changelog.read_text().splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
        elif current and line.startswith("- "):
            sections.setdefault(current, []).append(line[2:])
    return sections


def _collect_notes(old: str | None) -> list[str]:
    old_t = _ver_tuple(old) if old else (0, 0, 0)
    notes: list[str] = []
    for ver_str, items in sorted(_parse_changelog().items()):
        if _ver_tuple(ver_str) > old_t:
            notes.extend(items)
    return notes


def _write_version(version_file: Path, old: str | None) -> None:
    notes = _collect_notes(old)
    lines = [VERSION]
    if notes:
        lines.append("")
        lines.extend(f"- {note}" for note in notes)
    version_file.write_text("\n".join(lines) + "\n")


def ensure_structure(root: Path) -> None:
    version_file = root / ".version"
    old = _read_version(version_file)
    if old == VERSION:
        return

    for d in (HUMAN_DATA, AGENT_DATA, "insights", "memory", "accounts"):
        (root / d).mkdir(exist_ok=True)

    (root / "AGENT.md").write_text(_agent_md())
    (root / "CLAUDE.md").write_text("@AGENT.md\n")
    (root / ".python").write_text(sys.executable)
    _merge_claude_settings(root)
    _update_shipped_skills(root)

    _write_version(version_file, old)


MANAGED_CLAUDE_SETTINGS: dict[str, object] = {
    "autoMemoryEnabled": True,
    "autoMemoryDirectory": "memory",
    "hooks": {
        "SessionStart": [
            {
                "matcher": "startup|resume",
                "hooks": [
                    {
                        "type": "command",
                        "command": "cat .version 2>/dev/null || true",
                    }
                ],
            }
        ],
    },
}


def _merge_claude_settings(root: Path) -> None:
    import json

    settings_path = root / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)

    existing: dict[str, object] = {}
    if settings_path.exists():
        existing = json.loads(settings_path.read_text())

    existing.update(MANAGED_CLAUDE_SETTINGS)
    settings_path.write_text(json.dumps(existing, indent=2) + "\n")


def _update_shipped_skills(root: Path) -> None:
    skills_dst = root / SKILLS_DST
    skills_src = Path(__file__).resolve().parent.parent.parent / SKILLS_SRC
    skills_dst.mkdir(parents=True, exist_ok=True)

    if not skills_src.is_dir():
        return

    for skill in skills_src.iterdir():
        if not skill.is_dir():
            continue
        target = skills_dst / skill.name
        target.mkdir(exist_ok=True)
        _merge_skill(skill, target)


def _merge_skill(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            target.mkdir(exist_ok=True)
            _merge_skill(item, target)
        else:
            shutil.copy2(item, target)


def _agent_md() -> str:
    from lafmm.agent_prompt import AGENT_PROMPT

    return AGENT_PROMPT


# ── Profile ──────────────────────────────────────────────────────────

PROFILE_MD = """\
# Profile

## Experience
<!-- PLACEHOLDER: e.g., "2 years trading US equities, started with ETFs" -->

## Risk Tolerance
<!-- PLACEHOLDER: max drawdown you can stomach, e.g., "15% max drawdown" -->

## Goals
<!-- PLACEHOLDER: e.g., "grow capital 15-20% annually, learn systematically" -->

## Known Biases
<!-- PLACEHOLDER: patterns you want the agent to flag, e.g., "I hold losers too long" -->

## Trading System

### Entry Criteria
<!-- PLACEHOLDER: what signals do you act on? -->

### Exit Criteria
<!-- PLACEHOLDER: when do you get out? -->

### Position Sizing
<!-- PLACEHOLDER: method, e.g., "2% risk per trade, half-Kelly" -->

### Concentration Limits
<!-- PLACEHOLDER: e.g., "max 5 positions, max 30% in one sector" -->

### Holding Period
<!-- PLACEHOLDER: e.g., "swing trades, 2-10 days" -->

### Hard Rules
<!-- PLACEHOLDER: rules you never break, e.g., "never average down" -->
"""


def _scaffold_config(root: Path) -> None:
    config = root / "config.toml"
    if not config.exists():
        config.write_text("# Workspace-wide settings.\n# API keys, preferences.\n")


def _scaffold_profile(root: Path) -> None:
    (root / "profile.md").write_text(PROFILE_MD)


# ── Insights ────────────────────────────────────────────────────────


def _scaffold_insights(root: Path) -> None:
    insights = root / "insights"
    insights.mkdir()
    year = str(date.today().year)
    (insights / f"{year}.md").write_text(f"# Agent Insights — {year}\n")


# ── Accounts ─────────────────────────────────────────────────────────


def _scaffold_accounts(root: Path) -> None:
    accounts = root / "accounts"
    accounts.mkdir()


# ── Claude Code Configuration ───────────────────────────────────────


def _configure_claude(root: Path) -> None:
    claude_dir = root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)
    _merge_claude_settings(root)


# ── Skills ───────────────────────────────────────────────────────────


def _copy_skills(root: Path) -> None:
    skills_dst = root / SKILLS_DST
    skills_src = Path(__file__).resolve().parent.parent.parent / SKILLS_SRC
    skills_dst.parent.mkdir(parents=True, exist_ok=True)
    if skills_src.is_dir():
        shutil.copytree(skills_src, skills_dst)
    else:
        skills_dst.mkdir(exist_ok=True)


# ── US Indices ───────────────────────────────────────────────────────


def _write_group_toml(
    toml_path: Path,
    swing_pct: float,
    confirm_pct: float,
) -> None:
    toml_path.write_text(
        f'name = "US Indices"\n'
        f'leaders = ["SPY", "QQQ"]\n'
        f"swing_pct = {swing_pct}\n"
        f"confirm_pct = {confirm_pct}\n"
    )


def _scaffold_us_indices(root: Path) -> None:
    group_dir = root / HUMAN_DATA / US_INDICES_GROUP
    group_dir.mkdir(parents=True, exist_ok=True)
    _write_group_toml(
        group_dir / "group.toml",
        FALLBACK_SWING_PCT,
        FALLBACK_CONFIRM_PCT,
    )

    for ticker in (*US_INDICES_LEADERS, *US_INDICES_TRACKED):
        ticker_dir = group_dir / ticker
        ticker_dir.mkdir(exist_ok=True)
        csv_path = ticker_dir / f"{date.today().year}.csv"
        if not csv_path.exists():
            csv_path.write_text("date,open,high,low,close,volume\n")


def _tune_us_indices(root: Path) -> None:
    atr_script = root / SKILLS_DST / "tune-thresholds" / "scripts" / "atr.py"
    if not atr_script.exists():
        return

    group_dir = root / HUMAN_DATA / US_INDICES_GROUP
    result = subprocess.run(
        [sys.executable, str(atr_script), str(group_dir), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return

    import json

    data = json.loads(result.stdout)
    swing_pct = float(data["swing_pct"])
    confirm_pct = float(data["confirm_pct"])
    _write_group_toml(group_dir / "group.toml", swing_pct, confirm_pct)


def _fetch_us_indices(root: Path) -> None:
    fetch_script = root / SKILLS_DST / "fetch-prices" / "scripts" / "fetch.py"
    if not fetch_script.exists():
        return

    year = str(date.today().year)
    start = f"{year}-01-01"
    group_dir = root / HUMAN_DATA / US_INDICES_GROUP

    for ticker in (*US_INDICES_LEADERS, *US_INDICES_TRACKED):
        csv_path = group_dir / ticker / f"{year}.csv"
        result = subprocess.run(
            [sys.executable, str(fetch_script), ticker, "--csv", str(csv_path), "--start", start],
            check=False,
        )
        if result.returncode != 0:
            print(f"warning: failed to fetch {ticker}", file=sys.stderr)
