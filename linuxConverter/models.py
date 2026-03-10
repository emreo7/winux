from dataclasses import dataclass, field
from typing import List


@dataclass
class ParsedCommand:
    command: str
    flags: List[str]
    args: List[str]
    raw: str


@dataclass
class Pipeline:
    segments: List[ParsedCommand]


@dataclass
class TranslationResult:
    translated: str
    warnings: List[str] = field(default_factory=list)
    unsupported: List[str] = field(default_factory=list)

    def merge(self, other: "TranslationResult") -> None:
        self.warnings.extend(other.warnings)
        self.unsupported.extend(other.unsupported)
