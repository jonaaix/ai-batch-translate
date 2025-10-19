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

# Language priority for finding a source text
SOURCE_LANG_PRIORITY = ["de", "en", "fr"]


class FileProcessor:
    """Encapsulates all logic for processing a single file located in the processing directory."""

    def __init__(self, processing_path: Path, args: argparse.Namespace, system_prompt: str):
        self.processing_path = processing_path
        self.args = args
        self.system_prompt = system_prompt
        self.jsonl_path = self.processing_path.with_suffix(".jsonl")
        self.progress_path = self.processing_path.with_suffix(".progress")

    @staticmethod
    def _is_language_key(key: str) -> bool:
        """Check if a key is a 2-letter language code."""
        return len(key) == 2

    def _get_source_language(self, item: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """Finds the best available source language based on priority."""
        for lang in SOURCE_LANG_PRIORITY:
            if item.get(lang) and self._is_language_key(lang):
                return lang, item[lang]
        for lang, text in item.items():
            if self._is_language_key(lang) and text:
                return lang, text
        return None

    def _translate_item(self, item: Dict[str, Any], item_index: int, batch_start_index: int) -> Dict[str, Any]:
        """Handles the translation logic for a single item."""
        lang_values = {k: v for k, v in item.items() if self._is_language_key(k)}
        missing = [k for k, v in lang_values.items() if not v]

        if not missing:
            tqdm.write(f"Item #{item_index} is already fully translated.")
            return item

        source_info = self._get_source_language(item)
        if not source_info:
            tqdm.write(f"[ERROR] Item #{item_index}: No valid source text found.")
            return item

        source_lang, source_text = source_info

        if (item_index - batch_start_index) % self.args.batch_size == 0:
            user_prompt_example = f"{source_text} /no_think"
            logging.debug(f"Batch start prompt for item #{item_index}: {user_prompt_example}")

        translations = call_ai_translation_api(source_text, self.system_prompt, self.args.model)

        if translations:
            for lang_code, text in translations.items():
                if lang_code in missing:
                    item[lang_code] = text
            tqdm.write(f"Item #{item_index} successfully translated.")
        else:
            tqdm.write(f"[ERROR] Translation failed for item #{item_index}.")

        return item

    def _process_item_wrapper(
        self,
        item_index: int,
        item: Dict[str, Any],
        batch_start_index: int
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Wraps the logic from the old single-threaded loop for use in a thread pool.
        Returns the original index and the processed item, or None if skipped.
        """
        try:
            # This logic is from your working snapshot's run() loop
            available_langs = [k for k, v in item.items() if self._is_language_key(k) and v]
            if len(available_langs) < 1:
                tqdm.write(f"Item #{item_index} has 0 languages. Skipping.")
                return item_index, None  # None indicates "skip"

            # This logic calls your working snapshot's translate function
            processed_item = self._translate_item(item, item_index, batch_start_index)
            return item_index, processed_item

        except Exception as e:
            # Catch errors within the thread to avoid killing the whole pool
            tqdm.write(f"[CRITICAL_THREAD_ERROR] Item #{item_index} failed: {e}")
            logging.error(f"Error processing item #{item_index}: {e}", exc_info=True)
            # Return original item on failure, so progress can advance
            return item_index, item

    def run(self) -> None:
        """Orchestrates the processing of the file already in the processing directory."""
        logging.info(f"--- Starting processing for {self.processing_path.name} ---")

        try:
            with open(self.processing_path, "r", encoding="utf-8") as f:
                source_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read source file {self.processing_path.name}: {e}")
            return

        resume_index = read_progress(self.progress_path)
        if resume_index > 0:
            logging.info(f"Resuming at item #{resume_index} from {self.progress_path.name}.")

        if resume_index >= len(source_data):
            logging.info("All source items evaluated. Finalizing.")
            finalize_and_cleanup(self.processing_path, self.args.done_dir)
            return

        # --- NEW THREADED LOGIC ---

        # 1. Prepare items to process (from the resume_index onwards)
        items_to_process = []
        for i in range(resume_index, len(source_data)):
            items_to_process.append((i, source_data[i]))  # Tuple: (original_index, item_data)

        if not items_to_process:
            logging.info("No items left to process.")
            finalize_and_cleanup(self.processing_path, self.args.done_dir)
            return

        # Get worker count from args (added to config.py)
        num_workers = getattr(self.args, "workers", 1)  # Default to 1 if arg is missing
        logging.info(f"Starting job with {num_workers} worker threads.")

        # This is the next sequential index we must write to the file.
        next_index_to_write = resume_index

        # Buffer for results that finish out of order
        results_buffer: Dict[int, Optional[Dict[str, Any]]] = {}

        processing_completed = False

        try:
            write_mode = "a" if resume_index > 0 else "w"
            with open(self.jsonl_path, write_mode, encoding="utf-8") as jsonl_file:
                with ThreadPoolExecutor(max_workers=num_workers) as executor:

                    futures = {
                        executor.submit(self._process_item_wrapper, i, item, resume_index): i
                        for (i, item) in items_to_process
                    }

                    progress_bar = tqdm(
                        initial=0,  # This bar tracks *completed* items
                        total=len(items_to_process),
                        desc=f"Processing {self.processing_path.name}",
                        unit=" items"
                    )

                    with progress_bar:
                        for future in as_completed(futures):
                            # 1. A thread finished (out of order)
                            original_index, processed_item = future.result()

                            results_buffer[original_index] = processed_item
                            progress_bar.update(1)

                            # 2. Try to flush the buffer *in order*
                            while next_index_to_write in results_buffer:
                                # Get the item for the *correct* index
                                buffered_item = results_buffer.pop(next_index_to_write)

                                # A) Write item to .jsonl (if it wasn't skipped)
                                if buffered_item:
                                    jsonl_file.write(json.dumps(buffered_item, ensure_ascii=False) + "\n")

                                # --- FIX: Force flush to disk immediately ---
                                jsonl_file.flush()

                                # B) Update progress file to point to the *next* item
                                write_progress(self.progress_path, next_index_to_write + 1)

                                # C) Increment the pointer
                                next_index_to_write += 1

                        # Final flush in case the loop finishes but buffer logic didn't
                        jsonl_file.flush()

                        # 3. Check if we finished the whole file
                        if next_index_to_write == len(source_data):
                            processing_completed = True
                        else:
                            logging.info(
                                f"Processing loop finished. Progress saved up to item {next_index_to_write - 1}.")

        except (IOError, Exception) as e:
            # We still catch *other* errors to log progress
            logging.critical(f"An unexpected error occurred during processing: {e}")
            logging.info(f"Progress saved up to item {next_index_to_write - 1}. Job will resume.")
            return  # Do not finalize

        # 4. Finalize
        if processing_completed:
            logging.info(f"All {len(source_data)} items processed.")
            finalize_and_cleanup(self.processing_path, self.args.done_dir)
        else:
            logging.info(
                f"Processing for {self.processing_path.name} was not fully completed. Files remain in 'processing'.")