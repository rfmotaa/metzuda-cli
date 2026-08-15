"""Defines vulnerability findings and their severity/source classifications."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    NONE = "NONE"


class Source(str, Enum):
    STATIC = "static"
    SEMANTIC = "semantic"


@dataclass
class Finding:
    id: str
    type: str
    severity: Severity
    source: Source
    file: str
    line: int
    column: int = 0
    rule_id: Optional[str] = None
    explanation: str = ""
    fix_prompt: str = ""
    code_snippet: str = ""

    def is_severe(self) -> bool:
        """Returns True if the finding has a HIGH or CRITICAL severity level."""
        return self.severity in (Severity.HIGH, Severity.CRITICAL)
