from typing import List

from .command_parser import parse_command
from .models import Pipeline, ParsedCommand


def parse_pipeline(line: str) -> Pipeline:
    """
    Detect and split a pipeline string into parsed command segments.
    """
    if "|" in line:
        raw_segments = [segment.strip() for segment in line.split("|")]
    else:
        raw_segments = [line.strip()]

    segments: List[ParsedCommand] = []
    for raw_segment in raw_segments:
        if not raw_segment:
            continue
        segments.append(parse_command(raw_segment))

    return Pipeline(segments=segments)
