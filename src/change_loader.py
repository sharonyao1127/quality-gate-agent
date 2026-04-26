from pathlib import Path


def load_change_text(paths: list[str]) -> str:
    """Load and concatenate change descriptions from diff, markdown, or yaml files."""
    chunks = []
    for path in paths:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Change file not found: {path}")
        chunks.append(file_path.read_text(encoding="utf-8"))
    return "\n\n".join(chunks)
