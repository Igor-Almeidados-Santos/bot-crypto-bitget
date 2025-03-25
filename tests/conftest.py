import asyncio
import json
import os
import pytest
from pathlib import Path  # Importa Path
from unittest.mock import MagicMock

from config.settings import SettingsManager


@pytest.fixture
async def settings():
    settings_manager = await SettingsManager()
    await settings_manager.load()  # Carrega as configurações na fixture
    return settings_manager


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Redefine event_loop como autouse para evitar warnings."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_singleton(settings):
    settings2 = await SettingsManager()
    assert settings is settings2


@pytest.mark.asyncio
async def test_load_save(tmp_path, settings):
    test_file = tmp_path / "test_settings.json"
    settings.file_path = test_file
    test_data = {
        "rsi_buy": 25,
        "rsi_sell": 75,
        "macd_fast": 10
    }
    with open(test_file, 'w') as f:
        json.dump(test_data, f)

    await settings.load()
    assert settings.rsi_buy == 25
    settings.rsi_buy = 30
    await settings.save()
    with open(test_file, 'r') as f:
        saved = json.load(f)
    assert saved["rsi_buy"] == 30


@pytest.mark.asyncio
async def test_load_creates_file(tmp_path):
    test_file = tmp_path / "test_settings.json"
    settings = await SettingsManager()
    settings.file_path = test_file
    await settings.load()
    assert test_file.exists()
    with open(test_file, 'r') as f:
        saved = json.load(f)
    assert saved["rsi_buy"] == 35  # Default value

