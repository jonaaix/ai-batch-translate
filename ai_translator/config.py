# File: ai_translator/config.py
import argparse
import logging
import os
import sys
from pathlib import Path

from colorlog import ColoredFormatter
# --- FIX: Import the correct class name with a leading underscore ---
from tqdm.contrib.logging import _TqdmLoggingHandler

# --- End FIX ---

# --- Constants ---
DEFAULT_BATCH_SIZE: int = 100
DEFAULT_API_DELAY_S: float = 0.0
DEFAULT_WORKERS: int = 8


def setup_logging(log_file: str = "processing.log") -> None:
    # ... (function remains unchanged)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    log_colors = {
        'DEBUG': 'white', 'INFO': 'green', 'WARNING': 'yellow',
        'ERROR': 'red', 'CRITICAL': 'bold_red',
    }
    console_formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s [%(levelname)s] - %(message)s',
        log_colors=log_colors
    )

    # --- FIX: Use the correct imported class name ---
    # This integrates logging with the tqdm progress bar to prevent deadlocks
    console_handler = _TqdmLoggingHandler()
    # --- End FIX ---

    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Batch translate JSON files.")

    parser.add_argument(
        "--workers", type=int, default=1,
        help="Number of parallel worker threads."
    )

    # The auto-tune feature is now enabled by default.
    parser.add_argument(
        "--no-auto-tune", dest='auto_tune', action='store_false',
        help="Disable the default auto-tuning of worker count."
    )
    # ... (rest of arguments are unchanged)
    parser.add_argument(
        "--todo-dir", type=Path, default=Path("data/todo"),
        help="Directory with files to process."
    )
    parser.add_argument(
        "--processing-dir", type=Path, default=Path("data/processing"),
        help="Directory for active processing."
    )
    parser.add_argument(
        "--done-dir", type=Path, default=Path("data/done"),
        help="Directory to move completed files to."
    )
    parser.add_argument(
        "--prompt-file", type=Path, default=Path("prompts/system/translator.md"),
        help="Path to the system prompt file."
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help="Items to process before a checkpoint."
    )
    parser.add_argument(
        "--api-delay", type=float, default=DEFAULT_API_DELAY_S,
        help="Delay in seconds between API calls."
    )
    parser.add_argument(
        "--model", type=str, default=os.getenv("AI_MODEL_NAME", "qwen/qwen3-8b"),
        help="The model name for the API request."
    )
    return parser.parse_args()