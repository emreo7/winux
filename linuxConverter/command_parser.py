import shlex
from typing import List

from .models import ParsedCommand


def parse_command(segment: str) -> ParsedCommand:
    """
    Parse a single command segment into a ParsedCommand model.
    """
    tokens: List[str] = shlex.split(segment)
    if not tokens:
        return ParsedCommand(command="", flags=[], args=[], raw=segment)

    command = tokens[0]
    flags: List[str] = []
    args: List[str] = []

    for token in tokens[1:]:
        if token.startswith("-"):
            flags.append(token)
        else:
            args.append(token)

    return ParsedCommand(command=command, flags=flags, args=args, raw=segment)
