import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    returncode: int


def execute_translation(target: str, command: str, cwd: Optional[str] = None) -> ExecutionResult:
    """
    Execute a translated command in the appropriate Windows shell.
    """
    if not command.strip():
        return ExecutionResult(stdout="", stderr="", returncode=0)

    if target == "powershell":
        args = ["powershell", "-NoLogo", "-NoProfile", "-OutputFormat", "Text", "-Command", command]
    else:
        args = ["cmd", "/d", "/c", command]

    encoding = "utf-8"
    errors = "replace"

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding=encoding,
            errors=errors,
            check=False,
            cwd=cwd,
        )
        return ExecutionResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
    except FileNotFoundError as exc:
        return ExecutionResult(
            stdout="",
            stderr=str(exc),
            returncode=127,
        )
