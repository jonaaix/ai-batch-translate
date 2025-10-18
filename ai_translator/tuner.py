# File: ai_translator/tuner.py
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from ai_translator.processing import FileProcessor

TUNE_CHUNK_SIZE = 20  # Number of items to test for each worker count
TUNE_IMPROVEMENT_THRESHOLD = 0.95  # Must be at least 5% faster to continue tuning


class WorkerTuner:
    """Finds the optimal number of workers for the current environment."""

    def __init__(self, processor: 'FileProcessor'):
        # This uses a forward reference to avoid circular imports
        self.processor = processor

    def _run_chunk(self, items: List[Tuple[int, Dict[str, Any]]], num_workers: int) -> float:
        """Process a chunk of items with a given number of workers and return the duration."""
        start_time = time.monotonic()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # We only need to submit the work, results are handled by the main processor's method
            futures = {executor.submit(self.processor._process_single_item, item) for item in items}
            for future in as_completed(futures):
                future.result()  # Wait for all to complete
        return time.monotonic() - start_time

    def auto_tune(self, items_to_process: List[Tuple[int, Dict[str, Any]]]) -> int:
        """Iteratively finds the best number of workers."""
        logging.info("--- Starting worker auto-tuning ---")
        best_workers = 1

        logging.info(f"Tuning: Testing with 1 worker...")
        baseline_duration = self._run_chunk(items_to_process[:TUNE_CHUNK_SIZE], 1)
        best_duration = baseline_duration
        logging.info(f"Tuning: 1 worker took {baseline_duration:.2f}s for {TUNE_CHUNK_SIZE} items.")

        current_workers = 2
        while True:
            # Ensure we have enough items left to conduct the next test run
            start_index = (current_workers - 1) * TUNE_CHUNK_SIZE
            end_index = current_workers * TUNE_CHUNK_SIZE
            if end_index > len(items_to_process):
                logging.warning("Not enough items left for further tuning.")
                break

            logging.info(f"Tuning: Testing with {current_workers} workers...")
            items_for_this_run = items_to_process[start_index:end_index]
            current_duration = self._run_chunk(items_for_this_run, current_workers)
            logging.info(f"Tuning: {current_workers} workers took {current_duration:.2f}s for {TUNE_CHUNK_SIZE} items.")

            # If the new time is not significantly better, we stop
            if current_duration >= best_duration * TUNE_IMPROVEMENT_THRESHOLD:
                logging.info(f"Tuning: Performance plateaued or degraded. Optimal workers: {best_workers}")
                break

            best_duration = current_duration
            best_workers = current_workers
            current_workers += 1

        logging.info(f"--- Auto-tuning complete. Using {best_workers} workers for the remainder. ---")
        return best_workers