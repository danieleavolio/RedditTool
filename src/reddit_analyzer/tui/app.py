"""The Textual application: five screens (modes) over the core, F1-F5 to switch."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from textual.app import App, SystemCommand
from textual.binding import Binding
from textual.screen import Screen

from reddit_analyzer.tui.screens.analysis import AnalysisScreen
from reddit_analyzer.tui.screens.browser import BrowserScreen
from reddit_analyzer.tui.screens.collect import CollectScreen
from reddit_analyzer.tui.screens.dashboard import DashboardScreen
from reddit_analyzer.tui.screens.dataset import DatasetScreen
from reddit_analyzer.tui.service import Service

MODES_HELP = [
    ("dashboard", "Dashboard", "f1"),
    ("collect", "New collection", "f2"),
    ("browser", "Browse posts", "f3"),
    ("dataset", "Datasets", "f4"),
    ("analysis", "Analysis", "f5"),
]


class RpaApp(App):
    TITLE = "Reddit Post Analyzer"
    CSS_PATH = Path(__file__).with_name("app.tcss")
    MODES = {
        "dashboard": DashboardScreen,
        "collect": CollectScreen,
        "browser": BrowserScreen,
        "dataset": DatasetScreen,
        "analysis": AnalysisScreen,
    }
    DEFAULT_MODE = "dashboard"
    BINDINGS = [
        *(Binding(key, f"go('{mode}')", label) for mode, label, key in MODES_HELP),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, service: Service | None = None) -> None:
        super().__init__()
        self.service = service or Service()
        self.collection: str | None = None  # the collection the screens currently look at
        self.pending_resume: int | None = None  # a run the collect screen should resume

    def action_go(self, mode: str) -> None:
        self.switch_mode(mode)

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        for mode, label, key in MODES_HELP:
            yield SystemCommand(
                f"Go to: {label}",
                f"Switch to this screen ({key.upper()})",
                lambda m=mode: self.switch_mode(m),
            )


def run() -> None:
    RpaApp().run()
