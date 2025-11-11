from typing import Generator
from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_rich_console() -> Generator[Mock, None, None]:
    """Автоматически мокает rich.console для всех тестов"""
    with pytest.MonkeyPatch().context() as mp:
        mock_console = Mock()
        mp.setattr("aassh.console", mock_console)
        yield mock_console


@pytest.fixture
def mock_subprocess() -> Generator[Mock, None, None]:
    """Фикстура для мока subprocess"""
    with pytest.MonkeyPatch().context() as mp:
        mock_subprocess = Mock()
        mp.setattr("aassh.subprocess", mock_subprocess)
        yield mock_subprocess
