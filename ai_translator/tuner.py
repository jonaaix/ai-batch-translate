# File: ai_translator/tuner.py
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any, Dict, List, Tuple
from statistics import mean

if TYPE_CHECKING:
    from ai_translator.processing import FileProcessor

# --- CONFIG ------------------------------------------------------------
TUNE_MEASURE_DURATION = 30          # seconds per test round
TUNE_IMPROVEMENT_THRESHOLD = 0.99   # require +1% improvement to continue
TUNE_VALIDATION_REPEAT = True       # revalidate plateau worker to confirm
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
                f.result()

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
        best = max(h["items_per_min"] for h in history)
        for i, h in enumerate(history):
            delta_prev = (
                f"{(h['items_per_min'] / history[i-1]['items_per_min'] - 1) * 100:+.1f}%"
                if i > 0 else "base"
            )
            delta_best = f"{(h['items_per_min'] / best - 1) * 100:+.1f}%"
            logging.info(f"{h['workers']:>8} │ {h['items_per_min']:>10.1f} │ {delta_prev:>10} │ {delta_best:>10}")
        logging.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ------------------------------------------------------------
    # Main auto-tune entrypoint
    # ------------------------------------------------------------
    def auto_tune(self, items_to_process: List[Tuple[int, Dict[str, Any]]]) -> int:
        logging.info("⚙️  --- Starting worker auto-tuning ---")
        logging.info("🔥 Running warmup batch to stabilize model...")
        warmup_items = items_to_process[:10]
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
                    if recheck_speed >= best_items_per_min * TUNE_IMPROVEMENT_THRESHOLD:
                        logging.info("")
                        logging.info("✅ Plateau confirmed after re-test. Stopping tuning.")
                        logging.info("✅ Plateau confirmed after re-test. Stopping tuning.")
                        logging.info("✅ Plateau confirmed after re-test. Stopping tuning.")
                        break
                    else:
                        logging.info("🌀 Re-test showed better results, continuing search...")
                        best_items_per_min = recheck_speed
                        continue
                else:
                    break

        # Final table
        self._print_table(history)

        # Triple log for visibility
        logging.info("")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info(f"🏁🏁🏁  Optimal workers ≈ {best_workers} → {best_items_per_min:.1f} items/min 🚀🚀🚀")
        logging.info("")
        return best_workers
