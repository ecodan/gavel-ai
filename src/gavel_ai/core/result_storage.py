"""
Result storage for gavel-ai evaluation results.

Provides JSONL-based storage for evaluation results with support for:
- Appending new results
- Loading existing results
- Re-judging support

Per Epic 4 Story 4.6: Results stored in JSONL format for analysis and re-judging.
"""

import json
import logging
from pathlib import Path
from typing import Iterator, List

from gavel_ai.models.runtime import EvaluationResult

logger = logging.getLogger(__name__)


class ResultStorage:
    """
    JSONL-based storage for evaluation results.

    Per Epic 4 Story 4.6: Each result is stored as a single JSON line in results.jsonl.
    Supports appending new results and loading existing results for analysis.
    """

    def __init__(self, results_file: Path):
        """
        Initialize result storage.

        Args:
            results_file: Path to results.jsonl file
        """
        self.results_file = Path(results_file)
        self.results_file.parent.mkdir(parents=True, exist_ok=True)

    def append(self, result: EvaluationResult) -> None:
        """
        Append a single evaluation result to the storage.

        Args:
            result: EvaluationResult to store

        Raises:
            IOError: If unable to write to results file
        """
        try:
            # Convert Pydantic model to JSON string
            json_line = result.model_dump_json() + "\n"

            # Append to file
            with open(self.results_file, "a") as f:
                f.write(json_line)

            logger.debug(
                f"Stored result for scenario '{result.scenario_id}' "
                f"variant '{result.variant_id}' to {self.results_file}"
            )

        except Exception as e:
            logger.error(f"Failed to write result to {self.results_file}: {e}")
            raise IOError(f"Failed to write result to {self.results_file}: {e}") from e

    def append_batch(self, results: List[EvaluationResult]) -> None:
        """
        Append multiple evaluation results to the storage.

        Args:
            results: List of EvaluationResults to store

        Raises:
            IOError: If unable to write to results file
        """
        try:
            with open(self.results_file, "a") as f:
                for result in results:
                    json_line = result.model_dump_json() + "\n"
                    f.write(json_line)

            logger.info(f"Stored {len(results)} results to {self.results_file}")

        except Exception as e:
            logger.error(f"Failed to write batch results to {self.results_file}: {e}")
            raise IOError(f"Failed to write batch results to {self.results_file}: {e}") from e

    def load_all(self) -> List[EvaluationResult]:
        """
        Load all evaluation results from storage.

        Returns:
            List of all EvaluationResults in storage

        Raises:
            IOError: If unable to read from results file
        """
        if not self.results_file.exists():
            logger.warning(f"Results file {self.results_file} does not exist")
            return []

        try:
            results: List[EvaluationResult] = []
            errors = 0

            with open(self.results_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        result = EvaluationResult(**data)
                        results.append(result)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Skipping invalid JSON on line {line_num} of {self.results_file}: {e}"
                        )
                        errors += 1
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Skipping unparseable result on line {line_num} of {self.results_file}: {e}"
                        )
                        errors += 1
                        continue

            if errors > 0:
                logger.warning(
                    f"Loaded {len(results)} results from {self.results_file} "
                    f"({errors} lines skipped due to errors)"
                )
            else:
                logger.info(f"Loaded {len(results)} results from {self.results_file}")
            return results

        except FileNotFoundError:
            logger.warning(f"Results file {self.results_file} does not exist")
            return []
        except Exception as e:
            logger.error(f"Failed to load results from {self.results_file}: {e}")
            raise IOError(f"Failed to load results from {self.results_file}: {e}") from e

    def iterate(self) -> Iterator[EvaluationResult]:
        """
        Iterate over evaluation results without loading all into memory.

        Yields:
            EvaluationResult instances one at a time

        Raises:
            IOError: If unable to read from results file
        """
        if not self.results_file.exists():
            logger.warning(f"Results file {self.results_file} does not exist")
            return

        try:
            with open(self.results_file, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        result = EvaluationResult(**data)
                        yield result
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Skipping invalid JSON on line {line_num} of {self.results_file}: {e}"
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Skipping unparseable result on line {line_num} of {self.results_file}: {e}"
                        )
                        continue

        except FileNotFoundError:
            logger.warning(f"Results file {self.results_file} does not exist")
            return
        except Exception as e:
            logger.error(f"Failed to iterate results from {self.results_file}: {e}")
            raise IOError(f"Failed to iterate results from {self.results_file}: {e}") from e

    def filter_by_scenario(self, scenario_id: str) -> List[EvaluationResult]:
        """
        Load results filtered by scenario ID.

        Args:
            scenario_id: Scenario identifier to filter by

        Returns:
            List of EvaluationResults for the specified scenario
        """
        results = self.load_all()
        return [r for r in results if r.scenario_id == scenario_id]

    def filter_by_variant(self, variant_id: str) -> List[EvaluationResult]:
        """
        Load results filtered by variant ID.

        Args:
            variant_id: Variant identifier to filter by

        Returns:
            List of EvaluationResults for the specified variant
        """
        results = self.load_all()
        return [r for r in results if r.variant_id == variant_id]

    def clear(self) -> None:
        """
        Clear all results from storage.

        Deletes the results file if it exists.
        """
        if self.results_file.exists():
            self.results_file.unlink()
            logger.info(f"Cleared results from {self.results_file}")
