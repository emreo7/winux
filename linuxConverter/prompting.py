import os
import shlex
from typing import Callable, List, Optional

SUPPORTED_WORDS: List[str] = [
    # filesystem
    "pwd", "ls", "cd", "mkdir", "touch", "rm", "cp", "mv", "ln", "find", "du", "df",
    "chmod", "chown",
    # text / content
    "cat", "echo", "grep", "head", "tail", "sort", "uniq", "wc", "diff", "sed", "awk",
    # system
    "ps", "kill", "sleep", "whoami", "date", "clear", "history", "env", "export",
    "which", "man", "uname", "uptime", "free",
    # archive
    "tar", "zip", "unzip",
    # network
    "ping", "curl", "wget", "ssh", "scp", "ifconfig", "ip", "netstat",
    # dev tools (passthrough)
    "git", "npm", "pip", "python", "python3", "node",
    # operators
    "|",
]

# Commands that complete directories only (no files)
DIR_ONLY_COMMANDS = {"cd", "mkdir", "find", "du", "ln"}


def build_command_completer():
    from prompt_toolkit.completion import WordCompleter

    return WordCompleter(SUPPORTED_WORDS, ignore_case=True)


def _fs_matches(base: str, prefix: str, dirs_only: bool) -> List[str]:
    """
    Return filesystem entries under `base` whose names start with `prefix`.
    If `prefix` contains a path separator, resolve the parent and match on basename.
    Returns paths relative to `base`, using forward slashes.
    """
    target_base = base
    target_prefix = prefix

    if os.path.sep in prefix or "/" in prefix:
        normalized = prefix.replace("/", os.path.sep)
        parent = os.path.dirname(normalized)
        target_base = os.path.abspath(os.path.join(base, parent))
        target_prefix = os.path.basename(normalized)

    matches: List[str] = []
    if not os.path.isdir(target_base):
        return matches

    try:
        for entry in os.scandir(target_base):
            if not entry.name.startswith(target_prefix):
                continue
            if dirs_only and not entry.is_dir(follow_symlinks=True):
                continue
            # Build the relative path back to base
            if target_base == base:
                rel = entry.name
            else:
                rel_parent = os.path.relpath(target_base, base)
                rel = os.path.join(rel_parent, entry.name)
            rel = rel.replace(os.path.sep, "/")
            # Append trailing slash for directories so users know it's a dir
            if entry.is_dir(follow_symlinks=True):
                rel += "/"
            matches.append(rel)
    except PermissionError:
        return matches

    return sorted(matches)


def _safe_split(text: str) -> Optional[List[str]]:
    """shlex.split, returning None if the text has an unclosed quote."""
    try:
        return shlex.split(text)
    except ValueError:
        return None


def _apply_completion(buffer, completion: str, partial: str) -> None:
    """
    Replace `partial` at the end of the buffer with `completion`.
    Inserts a space before the completion only when the buffer already
    has content and no trailing space (i.e. this is a new argument).
    """
    if partial:
        buffer.delete_before_cursor(len(partial))
        buffer.insert_text(completion)
    else:
        # No partial typed — insert space separator only if needed
        if buffer.text and not buffer.text.endswith(" "):
            buffer.insert_text(" ")
        buffer.insert_text(completion)


def build_key_bindings(cwd_provider: Callable[[], str]):
    from prompt_toolkit.key_binding import KeyBindings

    kb = KeyBindings()

    @kb.add("tab")
    def handle_tab(event) -> None:
        buffer = event.app.current_buffer
        full_text = buffer.document.text

        # Work on the last pipeline segment only
        segments = full_text.split("|")
        current_segment = segments[-1]
        current_stripped = current_segment.lstrip()

        tokens = _safe_split(current_stripped)

        # If unclosed quote or empty, do nothing
        if not tokens:
            return

        command = tokens[0].lower()
        trailing_space = current_stripped.endswith(" ")
        args = tokens[1:]

        dirs_only = command in DIR_ONLY_COMMANDS

        # The partial path being completed is the last arg (if no trailing space)
        partial = ""
        if args and not trailing_space:
            partial = args[-1]

        cwd = cwd_provider()
        matches = _fs_matches(cwd, partial, dirs_only=dirs_only)

        if not matches:
            return

        if len(matches) == 1:
            # Single match — complete inline
            completion = matches[0]
            # Strip trailing slash if it was already typed
            if partial.endswith("/") and completion.startswith(partial):
                completion = completion[len(partial):]
            _apply_completion(buffer, completion, partial)

        else:
            # Multiple matches — print them in columns then re-show the prompt
            # with the current input preserved
            _print_matches_columns(matches, event.app.output)
            # Redraw the prompt with the existing buffer content intact
            event.app.renderer.reset()
            event.app.current_buffer.set_document(buffer.document, bypass_readonly=True)

    return kb


def _print_matches_columns(matches: List[str], output) -> None:
    """Print matches in a compact column layout, like bash/zsh tab completion."""
    import shutil
    try:
        term_width = shutil.get_terminal_size(fallback=(80, 24)).columns
    except Exception:
        term_width = 80

    if not matches:
        return

    col_width = max(len(m) for m in matches) + 2
    cols = max(1, term_width // col_width)

    output.write_raw("\r\n")
    for i, match in enumerate(matches):
        output.write_raw(match.ljust(col_width))
        if (i + 1) % cols == 0:
            output.write_raw("\r\n")
    if len(matches) % cols != 0:
        output.write_raw("\r\n")
    output.flush()


def create_prompt_session(cwd_provider: Callable[[], str]):
    from prompt_toolkit import PromptSession

    key_bindings = build_key_bindings(cwd_provider)
    return PromptSession(key_bindings=key_bindings)
