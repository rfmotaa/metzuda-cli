"""Defines the abstract base class for analyzers in Metzuda."""

from abc import ABC, abstractmethod
from pathlib import Path

from metzuda.models.finding import Finding


class BaseAnalyzer(ABC):
    """Abstract base class representing a generic scanner analyzer."""

    @abstractmethod
    def analyze(self, files: list[Path]) -> list[Finding]:
        """Runs the analysis on a list of files and returns a list of Findings."""

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the analyzer tool/API is available and configured."""
