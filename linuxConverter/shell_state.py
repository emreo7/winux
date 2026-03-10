import os
from typing import List, Tuple


def resolve_directory(current_cwd: str, args: List[str]) -> Tuple[str, str | None]:
    """
    Resolve a target directory for a cd-like command relative to current_cwd.
    Returns (new_cwd, error_message).
    """
    if not args:
        return current_cwd, None

    target = args[0]
    expanded = os.path.expanduser(os.path.expandvars(target))
    if not os.path.isabs(expanded):
        expanded = os.path.abspath(os.path.join(current_cwd, expanded))

    if not os.path.isdir(expanded):
        return current_cwd, f"Directory not found: {expanded}"

    return expanded, None


def format_prompt_path(path: str) -> str:
    """
    Render a path for display in the prompt using forward slashes.
    """
    return os.path.abspath(path).replace("\\", "/")
