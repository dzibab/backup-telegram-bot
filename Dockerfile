FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY . .

# Install the package with dependencies
RUN pip install --no-cache-dir uv
RUN uv sync

# Create a non-root user to run the application
RUN useradd -m appuser
USER appuser

# Command to run the application
CMD ["uv", "run", "-m", "backup_telegram_bot.main"]