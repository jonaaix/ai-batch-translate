# File: ai_translator/main.py
import logging
import shutil
import sys
import time
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from ai_translator.config import parse_arguments, setup_logging
from ai_translator.processing import FileProcessor


def _get_files(directory: Path) -> List[Path]:
    """Helper to get sorted .json files."""
    return sorted(
        [f for f in directory.iterdir() if f.is_file() and f.suffix == ".json"]
    )


def run() -> None:
    """Main entry point of the application logic."""
    load_dotenv()
    setup_logging()
    args = parse_arguments()

    # Ensure all directories exist
    args.todo_dir.mkdir(exist_ok=True)
    args.processing_dir.mkdir(exist_ok=True)
    args.done_dir.mkdir(exist_ok=True)

    try:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except IOError as e:
        logging.critical(f"Could not read prompt file at {args.prompt_file}: {e}")
        sys.exit(1)

    # --- FIX: New 'while' loop logic to continuously check for files ---
    try:
        logging.info("Starting processing loop. Checking for jobs...")
        while True:
            # 1. Prioritize any job already in the processing directory
            processing_files = _get_files(args.processing_dir)
            if processing_files:
                logging.info(f"Found {len(processing_files)} interrupted job(s). Resuming first one.")
                file_path = processing_files[0]
                processor = FileProcessor(processing_path=file_path, args=args, system_prompt=system_prompt)
                processor.run()
                continue  # Re-start loop to check processing dir again

            # 2. Process new jobs from the todo directory
            todo_files = _get_files(args.todo_dir)
            if todo_files:
                logging.info(f"Found {len(todo_files)} new job(s). Starting first one.")
                source_path = todo_files[0]
                processing_path = args.processing_dir / source_path.name

                try:
                    shutil.move(source_path, processing_path)
                    logging.info(f"Moved {source_path.name} to processing directory.")
                except (IOError, OSError) as e:
                    logging.error(f"Could not move {source_path.name} to processing: {e}")
                    time.sleep(1) # Wait a second if move failed (e.g. file lock)
                    continue  # Skip this file and re-loop

                processor = FileProcessor(processing_path=processing_path, args=args, system_prompt=system_prompt)
                processor.run()
                continue  # Re-start loop to check processing/todo dirs again

            # 3. If we are here, both directories were empty.
            logging.info("Processing and todo directories are empty. Shutting down.")
            break  # Exit the while True loop

    except KeyboardInterrupt:
        logging.warning("--- SHUTDOWN REQUESTED (Ctrl+C) ---")
        logging.info("Application will exit. Run again to resume interrupted jobs.")
        sys.exit(0)
    # --- End FIX ---