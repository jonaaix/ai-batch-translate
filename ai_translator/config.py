# File: ai_translator/config.py
import argparse
import logging
import os
import sys
from pathlib import Path

from colorlog import ColoredFormatter

# --- Constants ---
DEFAULT_BATCH_SIZE: int = 100
DEFAULT_API_DELAY_S: float = 0.0


def setup_logging(log_file: str = "processing.log") -> None:
    """Configure logging to file (standard) and console (colored)."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Set root to DEBUG to capture all levels

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # File handler (no colors)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)  # File logger only logs INFO and above
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler (with colors)
    log_colors = {
        'DEBUG': 'white', 'INFO': 'green', 'WARNING': 'yellow',
        'ERROR': 'red', 'CRITICAL': 'bold_red',
    }
    console_formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s [%(levelname)s] - %(message)s',
        log_colors=log_colors
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG) # Console shows all levels
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    # (Rest of the function remains unchanged)
    parser = argparse.ArgumentParser(description="Batch translate JSON files.")
    parser.add_argument(
        "--todo-dir", type=Path, default=Path("data/todo"),
        help="Directory with files to process."
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