# File: ai_translator/processing.py
import argparse
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from ai_translator.services.ai_api import call_ai_translation_api

# Language priority for finding a source text
SOURCE_LANG_PRIORITY = ["de", "en", "fr"]


def is_language_key(key: str) -> bool:
    """Check if a key is a 2-letter language code."""
    return len(key) == 2


def _get_source_language(item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Finds the best available source language based on priority."""
    for lang in SOURCE_LANG_PRIORITY:
        if item.get(lang) and is_language_key(lang):
            return lang, item[lang]
    for lang, text in item.items():
        if is_language_key(lang) and text:
            return lang, text
    return None


def _read_progress(progress_path: Path) -> int:
    """Reads the last processed index from the .progress file."""
    if not progress_path.exists():
        return 0
    try:
        with open(progress_path, "r") as f:
            return int(f.read().strip())
    except (IOError, ValueError):
        logging.error(f"Could not read progress file {progress_path.name}. Starting from 0.")
        return 0


def _write_progress(progress_path: Path, index: int) -> None:
    """Writes the next index to be processed to the .progress file."""
    try:
        with open(progress_path, "w") as f:
            f.write(str(index))
    except IOError as e:
        logging.error(f"Could not write to progress file {progress_path.name}: {e}")


def _finalize_file(file_path: Path, jsonl_path: Path, progress_path: Path) -> bool:
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


def process_file(file_path: Path, args: argparse.Namespace, system_prompt: str) -> None:
    """Processes a file using an incremental append strategy with a dedicated progress file."""
    logging.info(f"--- Starting processing for {file_path.name} ---")
    jsonl_path = file_path.with_suffix(".jsonl")
    progress_path = file_path.with_suffix(".progress")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Could not read or parse source file {file_path.name}: {e}")
        return

    # --- Step 1: Determine resume index from the .progress file ---
    resume_index = _read_progress(progress_path)

    if resume_index > 0:
        logging.info(f"Resuming at source item #{resume_index} based on {progress_path.name}.")

    if resume_index >= len(source_data):
        logging.info("All source items evaluated. Attempting to finalize.")
        if _finalize_file(file_path, jsonl_path, progress_path):
            shutil.move(file_path, args.done_dir / file_path.name)
        return

    # --- Step 2: Process remaining items ---
    try:
        # Open in "append" mode if resuming, "write" mode if starting fresh
        write_mode = "a" if resume_index > 0 else "w"
        with open(jsonl_path, write_mode, encoding="utf-8") as jsonl_file_handle:
            for i in range(resume_index, len(source_data)):
                item = source_data[i]

                available_langs = [k for k, v in item.items() if is_language_key(k) and v]
                if len(available_langs) <= 1:
                    logging.warning(f"Item #{i} has <= 1 language. Skipping and not adding to final file.")
                else:
                    lang_values = {k: v for k, v in item.items() if is_language_key(k)}
                    missing = [k for k, v in lang_values.items() if not v]

                    logging.warning(f"Item #{i}: Available Languages: {available_langs} | Missing: {missing}")

                    if not missing:
                        logging.info(f"Item #{i} is already fully translated.")
                    else:
                        source_info = _get_source_language(item)
                        if not source_info:
                            logging.error(f"Skipping translation for item #{i}: No valid source text.")
                        else:
                            source_lang, source_text = source_info
                            if (i - resume_index) % args.batch_size == 0:
                                user_prompt_example = f"{source_text} /no_think"
                                logging.debug(
                                    f"--- Starting new batch, first user prompt example: ---\n{user_prompt_example}")

                            logging.info(f"Translating item #{i}: Source='{source_lang}', Targets={missing}")
                            translations = call_ai_translation_api(source_text, system_prompt, args.model)

                            if translations:
                                for lang_code, text in translations.items():
                                    if lang_code in missing: item[lang_code] = text
                                logging.info(f"Successfully translated item #{i}.")
                            else:
                                logging.error(f"Failed to get translation for item #{i}.")

                    jsonl_file_handle.write(json.dumps(item) + "\n")
                    jsonl_file_handle.flush()

                # CRITICAL: Update progress file *after* evaluating each item
                _write_progress(progress_path, i + 1)

    except IOError as e:
        logging.error(f"A file operation failed: {e}")
        return

    # --- Step 3: Finalize the file ---
    logging.info("All source items evaluated. Finalizing file.")
    if _finalize_file(file_path, jsonl_path, progress_path):
        shutil.move(file_path, args.done_dir / file_path.name)
    else:
        logging.error(f"File {file_path.name} could not be finalized. Please check logs.")