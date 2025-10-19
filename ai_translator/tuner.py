# File: ai_translator/tuner.py
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Dict, List, Tuple
from statistics import mean

if TYPE_CHECKING:
    from ai_translator.processing import FileProcessor

# --- CONFIG ------------------------------------------------------------
TUNE_MEASURE_DURATION = 5  # seconds per test round
TUNE_IMPROVEMENT_THRESHOLD = 0.99  # require +1% improvement to continue
TUNE_VALIDATION_REPEAT = True  # revalidate plateau worker to confirm


# ----------------------------------------------------------------------


class WorkerTuner:
    """Finds the optimal number of workers for current hardware."""

    def __init__(self, processor: 'FileProcessor'):
        self.processor = processor

    # ------------------------------------------------------------
    # Internal helper: run one timed batch
    # ------------------------------------------------------------
    def _run_chunk(self, items: List[Tuple[int, Dict[str, Any]]], num_workers: int) -> Tuple[int, float]:
        """Process as many items as possible in the defined measurement window."""
        processed_count = 0
        start_time = time.monotonic()
        cutoff_time = start_time + TUNE_MEASURE_DURATION

        def timed_task(item_tuple):
            nonlocal processed_count
            if time.monotonic() > cutoff_time:
                return
            _, item, status = self.processor._process_single_item(item_tuple)
            if status == "translated":
                processed_count += 1

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(timed_task, item) for item in items}
            for f in as_completed(futures):
                if time.monotonic() > cutoff_time:
                    break
                try:
                    f.result()  # Check for exceptions
                except Exception as e:
                    logging.error(f"[TUNER_ERROR] Task failed during test: {e}")

        duration = time.monotonic() - start_time
        items_per_min = (processed_count / duration) * 60 if duration > 0 else 0
        return processed_count, items_per_min

    # ------------------------------------------------------------
    # ASCII table for results
    # ------------------------------------------------------------
    def _print_table(self, history: List[Dict[str, Any]]):
        logging.info("")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info(f"{'Workers':>8} │ {'Items/min':>10} │ {'Δ vs prev':>10} │ {'Δ vs best':>10}")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not history:
            logging.warning("No tuning history recorded.")
            return

        # Sort history by worker count for clean output
        history.sort(key=lambda h: h["workers"])

        best = max(h["items_per_min"] for h in history)
        if best == 0:
            logging.warning("Tuning resulted in zero throughput.")
            best = 1  # Avoid division by zero

        for i, h in enumerate(history):
            delta_prev = (
                f"{(h['items_per_min'] / history[i - 1]['items_per_min'] - 1) * 100:+.1f}%"
                if i > 0 and history[i - 1]['items_per_min'] > 0 else "base"
            )
            delta_best = f"{(h['items_per_min'] / best - 1) * 100:+.1f}%"
            logging.info(f"{h['workers']:>8} │ {h['items_per_min']:>10.1f} │ {delta_prev:>10} │ {delta_best:>10}")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ------------------------------------------------------------
    # --- FIX: Phase 2: Binary Search Fine-Tuning (NEW) ---
    # ------------------------------------------------------------
    def _get_speed(
            self,
            w_count: int,
            tested_results: Dict[int, float],
            items_to_process: List[Tuple[int, Dict[str, Any]]],
            history: List[Dict[str, Any]]
    ) -> float:
        """Helper to run a test or retrieve a cached result."""
        if w_count not in tested_results:
            logging.info(f"🔎  Testing {w_count} workers...")
            processed, items_per_min = self._run_chunk(items_to_process, w_count)

            tested_results[w_count] = items_per_min
            history.append({
                "workers": w_count,
                "items_per_min": items_per_min,
                "processed": processed,
            })
            logging.info(f"🔎  {w_count} workers → {items_per_min:.1f} items/min ({processed} processed)")

        return tested_results[w_count]

    def _run_fine_tuning_bisection(
            self,
            items_to_process: List[Tuple[int, Dict[str, Any]]],
            history: List[Dict[str, Any]],
            best_workers: int,
            best_items_per_min: float
    ) -> Tuple[int, float]:
        """
        Runs a binary search for the peak performance.
        """
        logging.info("")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info(f"🔎  Phase 2: Fine-tuning (Binary Search) around {best_workers} workers...")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Create a map of all results we already have
        tested_results: Dict[int, float] = {h["workers"]: h["items_per_min"] for h in history}

        # Find the bounds for our search
        try:
            history_sorted = sorted(history, key=lambda h: h["workers"])
            best_history_index = next(i for i, h in enumerate(history_sorted) if h["workers"] == best_workers)

            # Low bound is the previous coarse step (or 1)
            low_bound = history_sorted[best_history_index - 1]["workers"] if best_history_index > 0 else 1
            # High bound is the next coarse step (which caused the plateau)
            high_bound = history_sorted[best_history_index + 1]["workers"]

        except (StopIteration, IndexError):
            logging.warning("Could not determine fine-tune bounds. Sticking with coarse result.")
            return best_workers, best_items_per_min

        logging.info(f"🔎  Searching for peak in range [{low_bound}, {high_bound}]...")

        # Keep track of the best result found during this fine-tuning
        best_fine_workers = best_workers
        best_fine_speed = best_items_per_min

        # Implement binary search for the peak
        low = low_bound
        high = high_bound

        while low <= high:
            mid = (low + high) // 2
            if mid == 0: break  # Safety break

            # Test mid
            mid_speed = self._get_speed(mid, tested_results, items_to_process, history)
            if mid_speed > best_fine_speed:
                best_fine_speed = mid_speed
                best_fine_workers = mid

            # We need to test one neighbor to know which way to go
            mid_plus_1_speed = self._get_speed(mid + 1, tested_results, items_to_process, history)
            if mid_plus_1_speed > best_fine_speed:
                best_fine_speed = mid_plus_1_speed
                best_fine_workers = mid + 1

            # Decide which half to discard
            if mid_speed < mid_plus_1_speed:
                # The peak is to the right
                low = mid + 2  # We already tested mid and mid+1
            else:
                # The peak is to the left (or at mid)
                high = mid - 1

        logging.info(f"🔎  Binary search complete. Best fine-tuned result: {best_fine_workers} workers.")
        return best_fine_workers, best_fine_speed

    # ------------------------------------------------------------
    # Main auto-tune entrypoint
    # ------------------------------------------------------------
    def auto_tune(self, items_to_process: List[Tuple[int, Dict[str, Any]]]) -> int:
        logging.info("⚙️  --- Phase 1: Starting worker auto-tuning (Coarse) ---")
        logging.info("🔥 Running warmup batch to stabilize model...")
        warmup_items = items_to_process[:1]  # Use 1 item for warmup
        self._run_chunk(warmup_items, 1)

        worker_candidates = [1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 256, 512]
        history: List[Dict[str, Any]] = []

        best_workers = 1
        best_items_per_min = 0

        for workers in worker_candidates:
            processed, items_per_min = self._run_chunk(items_to_process, workers)
            history.append({
                "workers": workers,
                "items_per_min": items_per_min,
                "processed": processed,
            })

            avg_last = mean([h["items_per_min"] for h in history[-2:]]) if len(history) > 1 else items_per_min

            logging.info("")
            logging.info(f"⚙️  {workers} workers → {items_per_min:.1f} items/min ({processed} processed)")
            logging.info(f"⚙️  Current average: {avg_last:.1f} items/min")

            # Improvement check
            if items_per_min > best_items_per_min * TUNE_IMPROVEMENT_THRESHOLD:
                best_items_per_min = max(best_items_per_min, items_per_min)
                best_workers = workers
            else:
                # Plateau detected → optional validation
                logging.info("")
                logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                logging.info("📉  Performance plateau detected — validating best worker again...")
                logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

                if TUNE_VALIDATION_REPEAT:
                    _, recheck_speed = self._run_chunk(items_to_process, best_workers)
                    if recheck_speed >= best_items_per_min * (TUNE_IMPROVEMENT_THRESHOLD ** 2):  # Loosen threshold
                        logging.info("")
                        logging.info("✅ Plateau confirmed after re-test. Proceeding to fine-tuning.")
                        break
                    else:
                        logging.info("🌀 Re-test showed better results, continuing coarse search...")
                        best_items_per_min = recheck_speed
                        history.append({"workers": best_workers, "items_per_min": recheck_speed, "processed": 0})
                        continue
                else:
                    break

        # --- FIX: Run Phase 2 (Binary Search Fine-Tuning) ---
        best_workers, best_items_per_min = self._run_fine_tuning_bisection(
            items_to_process,
            history,
            best_workers,
            best_items_per_min
        )

        # Final table
        self._print_table(history)

        # Triple log for visibility
        logging.info("")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info("")
        return best_workers