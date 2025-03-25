import asyncio
import aiofiles
import json
import os
import pytest
from pathlib import Path  # Importa Path
from unittest.mock import MagicMock

from config.settings import SettingsManager


@pytest.fixture
async def settings(tmp_path): # Fixture com escopo de função
    settings_manager = await SettingsManager()
    # Cria um arquivo de configurações temporário para cada teste
    temp_file = tmp_path / "settings.json"
    settings_manager.file_path = temp_file
    await settings_manager.load()
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
    settings_instance = await settings # Aguarda a fixture settings
    settings2 = await SettingsManager()
    await settings2.load()
    assert settings_instance is settings2 # Compara as instâncias

@pytest.mark.asyncio
async def test_load_save(tmp_path): # Remove a fixture settings
    settings = await SettingsManager()
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
    assert settings.settings.rsi_buy == 25 # Acessa através de settings.settings
    settings.settings.rsi_buy = 30 # Modifica através de settings.settings
    await settings.save()
    with open(test_file, 'r') as f:
        saved = json.load(f)
    assert saved["rsi_buy"] == 30

@pytest.mark.asyncio
async def test_load_creates_file(tmp_path):
    settings_manager = await SettingsManager()
    test_file = tmp_path / "settings.json"
    settings_manager.file_path = test_file
    await settings_manager.save()
    assert test_file.exists()

    await settings_manager.load()
    assert settings_manager.settings.rsi_buy == 35
