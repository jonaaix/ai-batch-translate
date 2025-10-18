# File: ai_translator/state_manager.py
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List


def read_progress(progress_path: Path) -> int:
    """Reads the last processed index from the .progress file."""
    if not progress_path.exists():
        return 0
    try:
        with open(progress_path, "r") as f:
            return int(f.read().strip())
    except (IOError, ValueError):
        logging.error(f"Could not read progress file {progress_path.name}. Starting from 0.")
        return 0


def write_progress(progress_path: Path, index: int) -> None:
    """Writes the next index to be processed to the .progress file."""
    try:
        with open(progress_path, "w") as f:
            f.write(str(index))
    except IOError as e:
        logging.error(f"Could not write to progress file {progress_path.name}: {e}")


def finalize_file(file_path: Path, jsonl_path: Path, progress_path: Path) -> bool:
    """Creates the final JSON file from the .jsonl file and cleans up."""
    logging.info(f"Finalizing {file_path.name} from {jsonl_path.name}.")
    final_json_path = file_path.with_suffix(".json.final")

    processed_data = []
    try:
        if not jsonl_path.exists():
            logging.warning(f"No .jsonl file found for {file_path.name}. Nothing to finalize.")
            if progress_path.exists(): progress_path.unlink()
            return True

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                processed_data.append(json.loads(line))

        with open(final_json_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        with open(final_json_path, "r", encoding="utf-8") as f:
            json.load(f)
        logging.info(f"Validation successful for {final_json_path.name}.")

        shutil.move(final_json_path, file_path)
        logging.info(f"Successfully created final file: {file_path.name}")

        jsonl_path.unlink()
        progress_path.unlink()
        return True

    except (IOError, json.JSONDecodeError, OSError) as e:
        logging.critical(f"CRITICAL: Failed to finalize {file_path.name}. Error: {e}")
        logging.critical(f"Progress is saved in {jsonl_path.name}. Manual recovery needed.")
        if final_json_path.exists():
            final_json_path.unlink()
        return False