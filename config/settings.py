import json
import os
import aiofiles
import asyncio

from typing import Any, Dict, Optional, Union
from pathlib import Path
from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator
from asyncio import Lock


class Settings(BaseModel):
    rsi_buy: int = 35
    rsi_sell: int = 65
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    risk_per_trade: float = 0.01
    leverage: int = 10
    symbol: str = "BTC/USDT:USDT"
    timeframe: str = "1m"
    take_profit_percent: float = 2.0
    stop_loss_percent: float = 1.0
    trailing_stop_distance: float = 0.5
    trade_frequency: int = 60
    error_sleep_time: int = 30
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    bitget_api_key: Optional[str] = None
    bitget_api_secret: Optional[str] = None
    bitget_passphrase: Optional[str] = None
    order_size: float = 0.1 # Add order_size with default value

    @field_validator("risk_per_trade")
    def risk_per_trade_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError("risk_per_trade must be greater than 0")
        return value

    @field_validator("leverage")
    def leverage_must_be_positive(cls, value):
        if value <= 0:
            raise ValueError("leverage must be greater than 0")
        return value


class SettingsManager:
    _instance = None
    _lock = asyncio.Lock()
    settings: Optional[Settings] = None
    file_path: Path = Path('settings.json')

    async def __new__(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.settings = None
        return cls._instance

    async def load(self):
        async with self._lock:
            try:
                async with aiofiles.open(self.file_path, 'r') as f:
                    data = json.loads(await f.read())
                    self.settings = Settings(**data)
                    logger.info(f"Configurações carregadas de {self.file_path}")
            except FileNotFoundError:
                logger.warning(f"Arquivo de configurações não encontrado: {self.file_path}. Carregando configurações padrão.")
                self.settings = Settings()
                await self.save()
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Erro ao analisar o arquivo de configurações: {e}. Carregando configurações padrão.")
                self.settings = Settings()
                await self.save()
            except Exception as e:
                logger.exception("Erro inesperado ao carregar configurações:")
                raise

    async def save(self):
        async with self._lock:
            try:
                async with aiofiles.open(self.file_path, 'w') as f:
                    await f.write(json.dumps(self.settings.model_dump(), indent=2)) # Usa model_dump
                    logger.info(f"Configurações salvas em {self.file_path}")
            except Exception as e:
                logger.exception("Erro ao salvar configurações:")

    def __getattr__(self, name: str) -> Any:
        if self.settings is None:
            raise RuntimeError("Settings not loaded. Call load() first.")
        return getattr(self.settings, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "settings" or name not in Settings.model_fields: # Usa model_fields
            super().__setattr__(name, value)
        elif self.settings is not None:
            setattr(self.settings, name, value)
        else:
            raise RuntimeError("Settings not loaded. Call load() first.")




