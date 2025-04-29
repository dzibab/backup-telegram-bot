#!/usr/bin/env python
"""
Backup functionality for the Telegram Bot
"""
import logging
from datetime import datetime

from smb.SMBConnection import SMBConnection

from backup_telegram_bot.config import (
    SMB_USERNAME,
    SMB_PASSWORD,
    SMB_SERVER,
    SMB_SERVER_NAME,
    SMB_SHARE,
    SMB_PORT,
    BACKUP_DIRECTORY,
)

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages file backups to an SMB server"""

    def __init__(self):
        """Initialize the backup manager with SMB connection details"""
        self.smb_username = SMB_USERNAME
        self.smb_password = SMB_PASSWORD
        self.smb_server = SMB_SERVER
        self.smb_server_name = SMB_SERVER_NAME
        self.smb_share = SMB_SHARE
        self.smb_port = SMB_PORT
        self.backup_directory = BACKUP_DIRECTORY

        # Check if all required SMB settings are provided
        self._check_settings()

    def _check_settings(self):
        """Check if all required SMB settings are provided"""
        required_settings = {
            "SMB_USERNAME": self.smb_username,
            "SMB_PASSWORD": self.smb_password,
            "SMB_SERVER": self.smb_server,
            "SMB_SHARE": self.smb_share,
        }
        missing = [key for key, value in required_settings.items() if not value]

        if missing:
            logger.error(f"Missing required SMB settings: {', '.join(missing)}")
            raise ValueError(f"Missing required SMB settings: {', '.join(missing)}")

    def connect(self):
        """Establish connection to the SMB server"""
        try:
            # Create the SMB connection
            conn = SMBConnection(
                self.smb_username,
                self.smb_password,
                "TelegramBackupBot",  # client_name
                self.smb_server_name,  # server_name
                use_ntlm_v2=True,
                is_direct_tcp=True,
            )

            # Connect to the server
            connected = conn.connect(self.smb_server, self.smb_port)

            if not connected:
                logger.error(f"Failed to connect to SMB server {self.smb_server}")
                return None

            return conn

        except Exception as e:
            logger.error(f"Error connecting to SMB server: {e}")
            return None

    def backup_file(self, file_path, original_filename):
        """
        Backup a file to the SMB server

        Args:
            file_path (str): Local path to the downloaded file
            original_filename (str): Original filename to preserve

        Returns:
            bool: True if backup was successful, False otherwise
        """
        conn = self.connect()
        if not conn:
            return False

        try:
            # Create a timestamped folder for the backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = f"{self.backup_directory.rstrip('/')}/{timestamp}"

            # Try to create the backup folder
            try:
                conn.createDirectory(self.smb_share, backup_folder)
            except Exception:
                # Directory might already exist or be created as part of the path
                pass

            # Open the local file for reading
            with open(file_path, "rb") as file_obj:
                # Upload the file to the SMB server
                upload_path = f"{backup_folder}/{original_filename}"
                conn.storeFile(self.smb_share, upload_path, file_obj)

            logger.info(f"Successfully backed up file to {upload_path}")
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error backing up file: {e}")
            if conn:
                conn.close()
            return False
