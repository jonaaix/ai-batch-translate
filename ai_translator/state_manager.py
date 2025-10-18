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


def finalize_and_cleanup(
        processing_path: Path,
        done_dir: Path
) -> bool:
    """Creates the final JSON in 'done' dir and cleans up 'processing' dir."""
    jsonl_path = processing_path.with_suffix(".jsonl")
    progress_path = processing_path.with_suffix(".progress")
    final_target_path = done_dir / processing_path.name

    logging.info(f"Finalizing {processing_path.name} to {done_dir.name}.")

    # Use a temporary file in the final destination for atomicity
    temp_final_path = final_target_path.with_suffix(".json.final")

    processed_data = []
    try:
        if not jsonl_path.exists():
            logging.warning(f"No .jsonl data found for {processing_path.name}. Moving original file to done.")
            shutil.move(processing_path, final_target_path)
            if progress_path.exists(): progress_path.unlink()
            return True

        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                processed_data.append(json.loads(line))

        with open(temp_final_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)

        # Atomically move the final file into place
        shutil.move(temp_final_path, final_target_path)
        logging.info(f"Successfully created final file: {final_target_path.name}")

        # Cleanup all files in the processing directory
        jsonl_path.unlink()
        progress_path.unlink()
        processing_path.unlink()  # Delete the original moved source file
        return True

    except (IOError, json.JSONDecodeError, OSError) as e:
        logging.critical(f"CRITICAL: Failed to finalize. Error: {e}")
        logging.critical(f"Working files are preserved in {processing_path.parent}.")
        if temp_final_path.exists():
            temp_final_path.unlink()
        return False