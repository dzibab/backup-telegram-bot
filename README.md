# Backup Telegram Bot

A Telegram bot that automatically backs up files from a single authorized user to an SMB file server.

## Features

- **Single user authentication**: Only responds to one authorized user by Telegram User ID
- **SMB file server integration**: Connects to an SMB file server for backups
- **Supports multiple file types**:
  - Documents
  - Photos
  - Videos
  - Audio files
  - Voice messages
  - Forwarded messages with files
- **Environment configuration**: Uses `.env` file for easy configuration

## Setup

### Prerequisites

- Python 3.8 or higher
- Access to a Telegram Bot Token (via [@BotFather](https://t.me/botfather))
- An SMB server with write permissions

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/dzibab/backup-telegram-bot.git
   cd backup-telegram-bot
   ```

2. Install the package with dependencies:
   ```
   pip install -e .
   ```

3. Create a `.env` file by copying the example:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file with your configuration details:
   ```
   vim .env
   ```

### Configuration

The bot uses environment variables loaded from a `.env` file for configuration. Your `.env` file should contain:

```
# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
AUTHORIZED_USER_ID=your_telegram_user_id

# SMB Connection Settings
SMB_USERNAME=your_smb_username
SMB_PASSWORD=your_smb_password
SMB_SERVER=your_smb_server_ip_or_hostname
SMB_SERVER_NAME=your_smb_server_name  # Optional, can be empty
SMB_SHARE=your_smb_share_name
SMB_PORT=445  # Default SMB port
BACKUP_DIRECTORY=/path/on/smb/share  # Default: root of the share
```

To get your Telegram User ID, you can send a message to [@userinfobot](https://t.me/userinfobot) on Telegram.

### Running the Bot

Run the bot with:

```
python -m backup_telegram_bot.main
```

Or set it up as a service for continuous operation.

## Usage

1. Start a conversation with your bot in Telegram by sending `/start`
2. The bot will verify if you're the authorized user and greet you
3. Send any file or forward a message containing a file, and the bot will:
   - Download the file
   - Upload it to the specified SMB share
   - Confirm the backup with a message

### Available Commands

- `/start` - Start the bot
- `/help` - Display help information
- `/status` - Check bot and SMB connection status

## License

[Apache License 2.0](LICENSE)