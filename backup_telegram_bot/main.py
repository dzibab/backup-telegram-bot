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


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stickers."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the sticker
    sticker = update.message.sticker
    if not sticker:
        await update.message.reply_text("No sticker found in the message.")
        return

    # Generate a filename for the sticker
    extension = "webp"
    if sticker.is_animated:
        extension = "tgs"
    elif sticker.is_video:
        extension = "webm"

    filename = f"sticker_{sticker.file_unique_id}.{extension}"

    await process_file(update, context, sticker, filename)


async def handle_animation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle animations (GIFs)."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the animation
    animation = update.message.animation
    if not animation:
        await update.message.reply_text("No animation found in the message.")
        return

    # Use file_name if available or generate one
    filename = animation.file_name if animation.file_name else f"animation_{animation.file_unique_id}.gif"

    await process_file(update, context, animation, filename)


async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle video notes (round videos)."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    # Process the video note
    video_note = update.message.video_note
    if not video_note:
        await update.message.reply_text("No video note found in the message.")
        return

    # Generate a filename for the video note
    filename = f"video_note_{video_note.file_unique_id}.mp4"

    await process_file(update, context, video_note, filename)


async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle forwarded messages that might contain files."""
    user_id = update.effective_user.id

    if not check_user_authorized(user_id):
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    message = update.message

    # Check if this is a forwarded message
    if not message.forward_date:
        return  # Not a forwarded message

    # Try to identify any media in the forwarded message
    media_types = [
        (message.document, message.document.file_name if message.document else None),
        (message.photo[-1] if message.photo else None, f"photo_{message.photo[-1].file_unique_id}.jpg" if message.photo else None),
        (message.video, message.video.file_name if message.video and message.video.file_name else f"video_{message.video.file_unique_id}.mp4" if message.video else None),
        (message.audio, message.audio.file_name if message.audio and message.audio.file_name else f"audio_{message.audio.file_unique_id}.mp3" if message.audio else None),
        (message.voice, f"voice_{message.voice.file_unique_id}.ogg" if message.voice else None),
        (message.sticker, f"sticker_{message.sticker.file_unique_id}.webp" if message.sticker else None),
        (message.animation, message.animation.file_name if message.animation and message.animation.file_name else f"animation_{message.animation.file_unique_id}.gif" if message.animation else None),
        (message.video_note, f"video_note_{message.video_note.file_unique_id}.mp4" if message.video_note else None),
    ]

    for media, filename in media_types:
        if media:
            # We found a supported media type, process it
            await process_file(update, context, media, filename)
            return

    # No supported media found in the forwarded message
    await update.message.reply_text("No files found in the forwarded message that I can back up.")


async def handle_generic_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Generic handler for all messages to catch any files that might have been missed.
    This is a fallback to ensure all files are captured.
    """
    # Skip command messages and messages we've already handled with more specific handlers
    if update.message.text and update.message.text.startswith('/'):
        return

    user_id = update.effective_user.id
    if not check_user_authorized(user_id):
        return

    message = update.message
    file_processed = False

    # Check for any type of file that might be present in the message
    if message.document:
        await process_file(update, context, message.document, message.document.file_name)
        file_processed = True

    if message.photo:
        photo = message.photo[-1]  # Get the largest photo
        await process_file(update, context, photo, f"photo_{photo.file_unique_id}.jpg")
        file_processed = True

    if message.video:
        filename = message.video.file_name if message.video.file_name else f"video_{message.video.file_unique_id}.mp4"
        await process_file(update, context, message.video, filename)
        file_processed = True

    if message.audio:
        filename = message.audio.file_name if message.audio.file_name else f"audio_{message.audio.file_unique_id}.mp3"
        await process_file(update, context, message.audio, filename)
        file_processed = True

    if message.voice:
        await process_file(update, context, message.voice, f"voice_{message.voice.file_unique_id}.ogg")
        file_processed = True

    if message.sticker:
        extension = "webp"
        if message.sticker.is_animated:
            extension = "tgs"
        elif message.sticker.is_video:
            extension = "webm"
        await process_file(update, context, message.sticker, f"sticker_{message.sticker.file_unique_id}.{extension}")
        file_processed = True

    if message.animation:
        filename = message.animation.file_name if message.animation.file_name else f"animation_{message.animation.file_unique_id}.gif"
        await process_file(update, context, message.animation, filename)
        file_processed = True

    if message.video_note:
        await process_file(update, context, message.video_note, f"video_note_{message.video_note.file_unique_id}.mp4")
        file_processed = True

    # We don't want to send "No file found" messages for regular text messages
    # So only respond if it seems like the user was trying to send a file
    if not file_processed and (message.caption or message.forward_date):
        await update.message.reply_text(
            "I didn't find any files to back up in this message. "
            "Please send me a file directly or forward a message containing a file."
        )


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

    # File handlers for specific file types
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.ANIMATION, handle_animation))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))

    # Handler for forwarded messages
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded_message))

    # Generic handler to catch any other files we might have missed
    # This should be registered last so it doesn't override more specific handlers
    application.add_handler(MessageHandler(filters.ALL, handle_generic_message))

    # Log startup
    logger.info("Starting bot...")
    if AUTHORIZED_USER_ID:
        logger.info(f"Authorized user ID: {AUTHORIZED_USER_ID}")
    else:
        logger.warning("No authorized user ID set! Set the AUTHORIZED_USER_ID environment variable.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
