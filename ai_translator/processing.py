# File: ai_translator/processing.py
import argparse
import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from tqdm import tqdm

from ai_translator.services.ai_api import call_ai_translation_api
from ai_translator.state_manager import finalize_and_cleanup, read_progress, write_progress
from ai_translator.tuner import WorkerTuner
from ai_translator.utils import get_source_language, is_language_key


class FileProcessor:
    """Orchestrates the processing of a single translation source file."""

    def __init__(self, processing_path: Path, args: argparse.Namespace, system_prompt: str):
        self.processing_path = processing_path
        self.args = args
        self.system_prompt = system_prompt
        self.jsonl_path = self.processing_path.with_suffix(".jsonl")
        self.progress_path = self.processing_path.with_suffix(".progress")

    def _process_single_item(self, item_tuple: Tuple[int, Dict[str, Any]]) -> Tuple[int, Optional[Dict[str, Any]]]:
        """Handles the logic for a single item: filtering, translation, and returning the result."""
        item_index, item = item_tuple

        available_langs = [k for k, v in item.items() if is_language_key(k) and v]
        if len(available_langs) <= 1:
            tqdm.write(f"Item #{item_index} has <= 1 valid language (Found: {available_langs}). Skipping.")
            return item_index, None  # None indicates the item should be skipped

        lang_values = {k: v for k, v in item.items() if is_language_key(k)}
        missing = [k for k, v in lang_values.items() if not v]
        if not missing:
            tqdm.write(f"Item #{item_index} is already fully translated.")
            return item_index, item

        source_info = get_source_language(item)
        if not source_info:
            tqdm.write(f"[ERROR] Item #{item_index}: No valid source text found.")
            return item_index, item

        source_lang, source_text = source_info
        translations = call_ai_translation_api(source_text, self.system_prompt, self.args.model)

        if translations:
            for lang_code, text in translations.items():
                if lang_code in missing:
                    item[lang_code] = text
            tqdm.write(f"Item #{item_index} successfully translated.")
        else:
            tqdm.write(f"[ERROR] Translation failed for item #{item_index}.")

        return item_index, item

    def run(self) -> None:
        """Main execution method for processing the file."""
        logging.info(f"--- Starting processing for {self.processing_path.name} ---")
        try:
            with open(self.processing_path, "r", encoding="utf-8") as f:
                source_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read source file {self.processing_path.name}: {e}")
            return

        resume_index = read_progress(self.progress_path)
        items_to_process = list(enumerate(source_data))[resume_index:]

        if not items_to_process:
            logging.info("All source items evaluated. Finalizing.")
            if finalize_and_cleanup(self.processing_path, self.args.done_dir):
                if self.processing_path.exists():
                    shutil.move(self.processing_path, self.args.done_dir)
            return

        num_workers = self.args.workers
        if self.args.auto_tune and len(items_to_process) > 40:  # Need enough items to tune
            tuner = WorkerTuner(self)
            num_workers = tuner.auto_tune(items_to_process)
        else:
            logging.info(f"Using fixed number of workers: {num_workers}")

        try:
            write_mode = "a" if resume_index > 0 else "w"
            with open(self.jsonl_path, write_mode, encoding="utf-8") as jsonl_file:
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self._process_single_item, item): item for item in items_to_process}

                    progress_bar = tqdm(total=len(items_to_process), desc=f"Processing {self.processing_path.name}",
                                        unit=" items")
                    with progress_bar:
                        results = {}
                        for future in as_completed(futures):
                            original_index, result_item = future.result()
                            results[original_index] = result_item
                            progress_bar.update(1)

                        logging.info("Writing results to .jsonl file in original order...")
                        for i, item_tuple in enumerate(items_to_process):
                            original_index = item_tuple[0]
                            if original_index in results:
                                result_item = results[original_index]
                                if result_item:
                                    jsonl_file.write(json.dumps(result_item) + "\n")
                            write_progress(self.progress_path, original_index + 1)
                        jsonl_file.flush()

        except (IOError, Exception) as e:
            logging.critical(f"An unexpected error occurred during processing: {e}")
            return

        finalize_and_cleanup(self.processing_path, self.args.done_dir)