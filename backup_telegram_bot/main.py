#!/usr/bin/env python
"""
Main module for the Backup Telegram Bot
"""
import logging
import os
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from backup_telegram_bot.backup import BackupManager
from backup_telegram_bot.config import AUTHORIZED_USER_ID, TELEGRAM_BOT_TOKEN

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid excessive log output
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def check_user_authorized(user_id: int) -> bool:
    """Check if the user is authorized to use the bot."""
    if not AUTHORIZED_USER_ID:
        logger.error("No authorized user ID set. Set AUTHORIZED_USER_ID environment variable.")
        return False

    return user_id == AUTHORIZED_USER_ID


# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        logger.warning(f"Unauthorized access attempt from user {user_id}")
        return

    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your backup bot. Use /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    help_text = (
        "I can help you back up files to your SMB server.\n\n"
        "Just send me any file, document, photo, video, or forward a message "
        "containing files, and I'll back them up automatically.\n\n"
        "Available commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/status - Check the bot and SMB connection status"
    )
    await update.message.reply_text(help_text)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check the status of the bot and SMB connection."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Try to connect to SMB server to test connection
    backup_manager = BackupManager()
    conn = backup_manager.connect()

    if conn:
        conn.close()
        status_text = (
            "✅ Bot is operational\n"
            "✅ SMB connection successful\n"
            f"Server: {backup_manager.smb_server}\n"
            f"Share: {backup_manager.smb_share}\n"
            f"Backup directory: {backup_manager.backup_directory}"
        )
    else:
        status_text = (
            "✅ Bot is operational\n"
            "❌ SMB connection failed\n"
            "Please check your SMB server settings."
        )

    await update.message.reply_text(status_text)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming documents and files."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the document
    document = update.message.document
    if not document:
        await update.message.reply_text("No document found in the message.")
        return

    await process_file(update, context, document, document.file_name)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photos."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Get the largest photo
    photos = update.message.photo
    if not photos:
        await update.message.reply_text("No photo found in the message.")
        return

    # Photo objects are sorted by size, get the largest one (highest resolution)
    photo = photos[-1]
    # Generate a filename with timestamp since photos don't have filenames
    filename = f"photo_{photo.file_unique_id}.jpg"

    await process_file(update, context, photo, filename)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming videos."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the video
    video = update.message.video
    if not video:
        await update.message.reply_text("No video found in the message.")
        return

    # Use file_name if available or generate one
    filename = video.file_name if video.file_name else f"video_{video.file_unique_id}.mp4"

    await process_file(update, context, video, filename)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming audio files."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the audio
    audio = update.message.audio
    if not audio:
        await update.message.reply_text("No audio found in the message.")
        return

    # Use file_name if available or generate one
    filename = audio.file_name if audio.file_name else f"audio_{audio.file_unique_id}.mp3"

    await process_file(update, context, audio, filename)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming voice messages."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the voice message
    voice = update.message.voice
    if not voice:
        await update.message.reply_text("No voice message found.")
        return

    # Generate a filename for the voice message
    filename = f"voice_{voice.file_unique_id}.ogg"

    await process_file(update, context, voice, filename)


async def process_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_obj, filename: str) -> None:
    """Process and backup a file from Telegram."""
    try:
        # Reply that we're processing the file
        status_message = await update.message.reply_text(f"Processing {filename}...")

        # Download the file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = temp_file.name

        # Get the file from Telegram
        file = await context.bot.get_file(file_obj.file_id)
        await file.download_to_drive(file_path)

        # Update status
        await status_message.edit_text(f"Backing up {filename}...")

        # Backup the file
        backup_manager = BackupManager()
        success = backup_manager.backup_file(file_path, filename)

        # Clean up the temp file
        os.unlink(file_path)

        if success:
            await status_message.edit_text(f"✅ Successfully backed up {filename}")
        else:
            await status_message.edit_text(f"❌ Failed to back up {filename}")

    except Exception as e:
        logger.error(f"Error processing file {filename}: {e}")
        # Try to send an error message if possible
        try:
            await update.message.reply_text(f"Error processing file: {e}")
        except Exception:
            pass


def main() -> None:
    """Start the bot."""

    if not TELEGRAM_BOT_TOKEN:
        logger.error("No bot token found. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))

    # File handlers
    application.add_handler(MessageHandler(filters.Document, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Log startup
    logger.info("Starting bot...")
    if AUTHORIZED_USER_ID:
        logger.info(f"Authorized user ID: {AUTHORIZED_USER_ID}")
    else:
        logger.warning("No authorized user ID set! Set the AUTHORIZED_USER_ID environment variable.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
