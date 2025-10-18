# File: ai_translator/main.py
import logging
import sys

from dotenv import load_dotenv

from ai_translator.config import parse_arguments, setup_logging
from ai_translator.processing import FileProcessor


def run() -> None:
    """Main entry point of the application logic."""
    load_dotenv()
    setup_logging()
    args = parse_arguments()

    args.done_dir.mkdir(exist_ok=True)
    args.todo_dir.mkdir(exist_ok=True)

    try:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except IOError as e:
        logging.critical(f"Could not read prompt file at {args.prompt_file}: {e}")
        sys.exit(1)

    files_to_process = sorted(
        [f for f in args.todo_dir.iterdir() if f.is_file() and f.suffix == ".json"]
    )

    if not files_to_process:
        logging.info("No JSON files found in the 'todo' directory.")
        return

    logging.info(f"Found {len(files_to_process)} files to process.")

    for file_path in files_to_process:
        processor = FileProcessor(
            file_path=file_path,
            args=args,
            system_prompt=system_prompt
        )
        processor.run()

    logging.info("All files processed.")