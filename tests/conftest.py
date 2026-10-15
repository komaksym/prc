from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from prc.fixture_source import FIXTURE_EPOCH, FixtureSource
from prc.model import PrRef
from prc.scenarios import SCENARIOS


class FakeClock:
    def __init__(self, start: float = FIXTURE_EPOCH) -> None:
        self.now = start

    def __call__(self) -> float:
        self.now += 1.0

        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def make_source(tmp_path: Path) -> Callable[[str], tuple[FixtureSource, PrRef]]:
    def make(name: str) -> tuple[FixtureSource, PrRef]:
        return SCENARIOS[name](tmp_path)

    return make
