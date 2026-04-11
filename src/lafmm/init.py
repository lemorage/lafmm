from pathlib import Path

LAFMM_DIR = ".lafmm"
HUMAN_DATA = "data"
AGENT_DATA = "cache"
SKILLS = "skills"


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
    (root / SKILLS).mkdir()
    (root / "AGENT.md").write_text(_agent_md())
    (root / "CLAUDE.md").write_text("@AGENT.md\n")
    return root


def _agent_md() -> str:
    from lafmm.agent_prompt import AGENT_PROMPT

    return AGENT_PROMPT
