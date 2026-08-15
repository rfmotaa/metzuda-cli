"""Defines configuration settings for the Metzuda scanner."""

from dataclasses import dataclass, field

from metzuda.models.finding import Severity


@dataclass
class MetzudaConfig:
    language: str = "auto"
    severity_threshold: Severity = Severity.HIGH
    ai_analysis: bool = True
    max_context_lines: int = 150
    logged_in: bool = False
    login_method: str = "none"
    email: str | None = None
    plan: str = "free"  # cached after login for offline display
    ignore_paths: list[str] = field(
        default_factory=lambda: [
            # Version Control
            ".git/",
            
            # JavaScript/TypeScript (Node, React, Next.js, Vue, Angular, Svelte)
            "node_modules/",
            "dist/",
            "build/",
            "out/",
            ".next/",
            ".nuxt/",
            ".svelte-kit/",
            "coverage/",
            ".cache/",
            "*.test.js",
            "*.spec.js",
            "*.test.ts",
            "*.spec.ts",
            
            # Python (Flask, Django, FastAPI, Pytest)
            "__pycache__/",
            ".venv/",
            "venv/",
            "env/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".tox/",
            "htmlcov/",
            "*.egg-info/",
            
            # Java (Maven, Gradle, Spring Boot, IDEs)
            "target/",
            ".gradle/",
            "bin/",
            "out/",
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            
            # Metzuda Cache/State
            ".metzuda/",
        ]
    )

    def should_run_ai(self) -> bool:
        """Returns True if AI analysis is enabled and the severity threshold is not LOW."""
        return self.ai_analysis and self.severity_threshold != Severity.LOW
