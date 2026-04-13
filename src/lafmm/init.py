import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

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


def get_root() -> Path | None:
    root = Path.home() / LAFMM_DIR
    return root if root.is_dir() else None


def scaffold() -> Path:
    root = Path.home() / LAFMM_DIR
    if root.exists():
        return root

    root.mkdir()
    (root / HUMAN_DATA).mkdir()
    (root / AGENT_DATA).mkdir()
    (root / "AGENT.md").write_text(_agent_md())
    (root / "CLAUDE.md").write_text("@AGENT.md\n")

    _copy_skills(root)
    _scaffold_us_indices(root)
    _fetch_us_indices(root)
    _tune_us_indices(root)

    return root


def _agent_md() -> str:
    from lafmm.agent_prompt import AGENT_PROMPT

    return AGENT_PROMPT


def _copy_skills(root: Path) -> None:
    skills_dst = root / SKILLS_DST
    skills_src = Path(__file__).resolve().parent.parent.parent / SKILLS_SRC
    skills_dst.parent.mkdir(parents=True, exist_ok=True)
    if skills_src.is_dir():
        shutil.copytree(skills_src, skills_dst)
    else:
        skills_dst.mkdir(exist_ok=True)


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
