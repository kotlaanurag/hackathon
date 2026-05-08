"""GitHub API: clone, tree, file fetch."""

from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path

from config.settings import get_settings


def clone_repo(repo_url: str, depth: int = 1) -> Path:
    """Clone a GitHub repository to a temporary directory."""
    settings = get_settings()
    tmp_dir = Path(tempfile.mkdtemp(prefix="repo_"))

    cmd = ["git", "clone", "--depth", str(depth)]
    if settings.github_token:
        # Inject token for private repos
        authed_url = repo_url.replace("https://", f"https://x-access-token:{settings.github_token}@")
        cmd.append(authed_url)
    else:
        cmd.append(repo_url)
    cmd.append(str(tmp_dir))

    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    return tmp_dir


def get_file_tree(repo_path: Path, extensions: list[str] | None = None) -> list[str]:
    """Get list of files in the repository."""
    if extensions is None:
        extensions = [".py", ".cs", ".ts", ".js", ".java", ".yaml", ".json"]

    files = []
    for f in repo_path.rglob("*"):
        if f.is_file() and f.suffix in extensions:
            files.append(str(f.relative_to(repo_path)))
    return sorted(files)


def fetch_file_content(repo_path: Path, relative_path: str) -> str:
    """Read a file from the cloned repository."""
    full_path = repo_path / relative_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8", errors="replace")
    return ""
