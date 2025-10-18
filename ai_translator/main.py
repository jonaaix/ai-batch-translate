# File: ai_translator/main.py
import logging
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from ai_translator.config import parse_arguments, setup_logging
from ai_translator.processing import FileProcessor


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

    # --- New Startup Logic ---

    # 1. Prioritize any job already in the processing directory
    processing_files = sorted(
        [f for f in args.processing_dir.iterdir() if f.is_file() and f.suffix == ".json"]
    )
    if processing_files:
        logging.info(f"Found {len(processing_files)} interrupted job(s). Resuming...")
        for file_path in processing_files:
            processor = FileProcessor(processing_path=file_path, args=args, system_prompt=system_prompt)
            processor.run()
    else:
        logging.info("No interrupted jobs found in processing directory.")

    # 2. Process new jobs from the todo directory
    todo_files = sorted(
        [f for f in args.todo_dir.iterdir() if f.is_file() and f.suffix == ".json"]
    )

    if not todo_files:
        logging.info("No new files to process in 'todo' directory.")
    else:
        logging.info(f"Starting {len(todo_files)} new jobs from 'todo' directory.")
        for source_path in todo_files:
            processing_path = args.processing_dir / source_path.name

            try:
                shutil.move(source_path, processing_path)
                logging.info(f"Moved {source_path.name} to processing directory.")
            except (IOError, OSError) as e:
                logging.error(f"Could not move {source_path.name} to processing: {e}")
                continue  # Skip to the next file

            processor = FileProcessor(processing_path=processing_path, args=args, system_prompt=system_prompt)
            processor.run()

    logging.info("All processing finished.")