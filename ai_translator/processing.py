# File: ai_translator/processing.py
import argparse
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from tqdm import tqdm

from ai_translator.services.ai_api import call_ai_translation_api
from ai_translator.state_manager import finalize_file, read_progress, write_progress

# Language priority for finding a source text
SOURCE_LANG_PRIORITY = ["de", "en", "fr"]


def _is_language_key(key: str) -> bool:
    """Check if a key is a 2-letter language code."""
    return len(key) == 2


def _get_source_language(item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Finds the best available source language based on priority."""
    for lang in SOURCE_LANG_PRIORITY:
        if item.get(lang) and _is_language_key(lang):
            return lang, item[lang]
    for lang, text in item.items():
        if _is_language_key(lang) and text:
            return lang, text
    return None


def _translate_item(item: Dict[str, Any], system_prompt: str, args: argparse.Namespace) -> Dict[str, Any]:
    """Handles the translation logic for a single item."""
    lang_values = {k: v for k, v in item.items() if _is_language_key(k)}
    missing = [k for k, v in lang_values.items() if not v]

    if not missing:
        tqdm.write(f"Item is already fully translated.")
        return item

    source_info = _get_source_language(item)
    if not source_info:
        tqdm.write(f"[ERROR] No valid source text found for this item.")
        return item

    source_lang, source_text = source_info

    # Log prompt example for the first item in a batch
    if (tqdm.n - args.initial) % args.batch_size == 0:
        user_prompt_example = f"{source_text} /no_think"
        logging.debug(f"Batch start prompt example: {user_prompt_example}")

    translations = call_ai_translation_api(source_text, system_prompt, args.model)

    if translations:
        for lang_code, text in translations.items():
            if lang_code in missing:
                item[lang_code] = text
        tqdm.write(f"Item successfully translated.")
    else:
        tqdm.write(f"[ERROR] Translation failed for this item.")

    return item


def process_file(file_path: Path, args: argparse.Namespace, system_prompt: str) -> None:
    """Orchestrates the processing of a single file."""
    logging.info(f"--- Starting processing for {file_path.name} ---")
    jsonl_path = file_path.with_suffix(".jsonl")
    progress_path = file_path.with_suffix(".progress")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Could not read source file {file_path.name}: {e}")
        return

    resume_index = read_progress(progress_path)
    if resume_index > 0:
        logging.info(f"Resuming at source item #{resume_index} based on {progress_path.name}.")

    if resume_index >= len(source_data):
        logging.info("All source items evaluated. Finalizing.")
        if finalize_file(file_path, jsonl_path, progress_path):
            shutil.move(file_path, args.done_dir / file_path.name)
        return

    try:
        write_mode = "a" if resume_index > 0 else "w"
        with open(jsonl_path, write_mode, encoding="utf-8") as jsonl_file:
            progress_bar = tqdm(
                initial=resume_index, total=len(source_data),
                desc=f"Processing {file_path.name}", unit=" items"
            )
            with progress_bar:
                for i in range(resume_index, len(source_data)):
                    item = source_data[i]
                    progress_bar.set_postfix_str(f"Item #{i}")

                    available_langs = [k for k, v in item.items() if _is_language_key(k) and v]
                    if len(available_langs) <= 1:
                        tqdm.write(f"Item #{i} has <= 1 language. Skipping.")
                    else:
                        processed_item = _translate_item(item, system_prompt, args)
                        jsonl_file.write(json.dumps(processed_item) + "\n")
                        jsonl_file.flush()

                    write_progress(progress_path, i + 1)
                    progress_bar.update(1)

    except IOError as e:
        logging.error(f"A file operation failed: {e}")
        return

    logging.info("All source items evaluated. Finalizing file.")
    if finalize_file(file_path, jsonl_path, progress_path):
        shutil.move(file_path, args.done_dir / file_path.name)
    else:
        logging.error(f"File {file_path.name} could not be finalized.")