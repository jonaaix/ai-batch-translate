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


class FileProcessor:
    """
    Encapsulates all logic for processing a single translation source file.
    """

    def __init__(self, file_path: Path, args: argparse.Namespace, system_prompt: str):
        self.file_path = file_path
        self.args = args
        self.system_prompt = system_prompt
        self.jsonl_path = file_path.with_suffix(".jsonl")
        self.progress_path = file_path.with_suffix(".progress")

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
            tqdm.write(f"[ERROR] Item #{item_index}: No valid source text found for this item.")
            return item

        source_lang, source_text = source_info

        # Log prompt example for the first item in a batch, using the passed-in index
        if (item_index - batch_start_index) % self.args.batch_size == 0:
            user_prompt_example = f"{source_text} /no_think"
            logging.debug(f"Batch start prompt example for item #{item_index}: {user_prompt_example}")

        translations = call_ai_translation_api(source_text, self.system_prompt, self.args.model)

        if translations:
            for lang_code, text in translations.items():
                if lang_code in missing:
                    item[lang_code] = text
            tqdm.write(f"Item #{item_index} successfully translated.")
        else:
            tqdm.write(f"[ERROR] Translation failed for item #{item_index}.")

        return item

    def run(self) -> None:
        """Orchestrates the processing of the file."""
        logging.info(f"--- Starting processing for {self.file_path.name} ---")

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                source_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read source file {self.file_path.name}: {e}")
            return

        resume_index = read_progress(self.progress_path)
        if resume_index > 0:
            logging.info(f"Resuming at source item #{resume_index} based on {self.progress_path.name}.")

        if resume_index >= len(source_data):
            logging.info("All source items evaluated. Finalizing.")
            if finalize_file(self.file_path, self.jsonl_path, self.progress_path):
                shutil.move(self.file_path, self.args.done_dir / self.file_path.name)
            return

        try:
            write_mode = "a" if resume_index > 0 else "w"
            with open(self.jsonl_path, write_mode, encoding="utf-8") as jsonl_file:
                progress_bar = tqdm(
                    initial=resume_index, total=len(source_data),
                    desc=f"Processing {self.file_path.name}", unit=" items"
                )
                with progress_bar:
                    for i in range(resume_index, len(source_data)):
                        item = source_data[i]
                        progress_bar.set_postfix_str(f"Item #{i}")

                        available_langs = [k for k, v in item.items() if self._is_language_key(k) and v]
                        if len(available_langs) <= 1:
                            tqdm.write(f"Item #{i} has <= 1 language. Skipping.")
                        else:
                            # Pass the current loop index 'i' to the method
                            processed_item = self._translate_item(item, i, resume_index)
                            jsonl_file.write(json.dumps(processed_item) + "\n")
                            jsonl_file.flush()

                        write_progress(self.progress_path, i + 1)
                        progress_bar.update(1)

        except IOError as e:
            logging.error(f"A file operation failed: {e}")
            return

        logging.info("All source items evaluated. Finalizing file.")
        if finalize_file(self.file_path, self.jsonl_path, self.progress_path):
            shutil.move(self.file_path, self.args.done_dir / self.file_path.name)
        else:
            logging.error(f"File {self.file_path.name} could not be finalized.")