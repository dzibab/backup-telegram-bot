#!/usr/bin/env python
"""
Configuration module for Backup Telegram Bot
Loads environment variables from .env file
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.environ.get("AUTHORIZED_USER_ID", 0))

# SMB Connection Settings
SMB_USERNAME = os.environ.get("SMB_USERNAME")
SMB_PASSWORD = os.environ.get("SMB_PASSWORD")
SMB_SERVER = os.environ.get("SMB_SERVER")
SMB_SERVER_NAME = os.environ.get("SMB_SERVER_NAME", "")
SMB_SHARE = os.environ.get("SMB_SHARE")
SMB_PORT = int(os.environ.get("SMB_PORT", 445))
BACKUP_DIRECTORY = os.environ.get("BACKUP_DIRECTORY", "/")