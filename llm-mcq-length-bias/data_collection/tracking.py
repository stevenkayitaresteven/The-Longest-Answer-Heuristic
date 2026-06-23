"""
tracking.py
===========
Experiment-tracking abstraction with three backends behind one interface:

  * ``JsonlTracker`` (default) -- zero dependencies; writes params/metrics/manifest
    as JSON-lines under the run directory. Always available, fully reproducible.
  * ``MLflowTracker``          -- logs params, metrics, and artifacts to MLflow.
  * ``NullTracker``            -- no-op (for tests / dry runs).

RECOMMENDATION (see REAL_COLLECTION_PLAN.md): use **MLflow** for the real study.
Rationale: it is open-source, runs fully locally against a file store (``file:./
mlruns``) with no account or network dependency, logs params/metrics/artifacts and
diffs runs out of the box, and integrates with the JSONL provenance we already
write. Weights & Biases is excellent but is cloud-first (account + network);
Sacred is lighter but less maintained and needs a separate store (e.g. MongoDB)
for its best features. For a reproducible, offline-capable, audit-friendly
collection harness, MLflow is the best fit; ``JsonlTracker`` is the dependency-free
fallback and is the default so the pipeline runs anywhere.
"""
from __future__ import annotations

import abc
import json
import logging
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("data_collection.tracking")


class ExperimentTracker(abc.ABC):
    @abc.abstractmethod
    def log_params(self, params: dict[str, Any]) -> None: ...
    @abc.abstractmethod
    def log_metrics(self, metrics: dict[str, float]) -> None: ...
    @abc.abstractmethod
    def log_artifact(self, path: str) -> None: ...
    def close(self) -> None:  # optional override
        pass


class NullTracker(ExperimentTracker):
    def log_params(self, params): pass
    def log_metrics(self, metrics): pass
    def log_artifact(self, path): pass


class JsonlTracker(ExperimentTracker):
    """Dependency-free tracker: appends JSON lines under ``run_dir``."""

    def __init__(self, run_dir: str, run_id: str):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self._path = self.dir / "tracking.jsonl"

    def _emit(self, kind: str, payload: dict) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"run_id": self.run_id, "kind": kind,
                                "payload": payload}, ensure_ascii=False) + "\n")

    def log_params(self, params): self._emit("params", params)
    def log_metrics(self, metrics): self._emit("metrics", metrics)
    def log_artifact(self, path): self._emit("artifact", {"path": str(path)})


class MLflowTracker(ExperimentTracker):
    """MLflow-backed tracker (lazy import; raises clearly if MLflow is absent)."""

    def __init__(self, experiment_name: str, run_id: str,
                 uri: Optional[str] = None):
        try:
            import mlflow
        except ImportError as e:  # explicit, never silent
            raise RuntimeError("tracking.backend='mlflow' requires mlflow "
                               "(`pip install mlflow`)") from e
        self._mlflow = mlflow
        if uri:
            mlflow.set_tracking_uri(uri)
        mlflow.set_experiment(experiment_name)
        self._run = mlflow.start_run(run_name=run_id)

    def log_params(self, params): self._mlflow.log_params(
        {k: str(v) for k, v in params.items()})
    def log_metrics(self, metrics): self._mlflow.log_metrics(
        {k: float(v) for k, v in metrics.items()})
    def log_artifact(self, path): self._mlflow.log_artifact(path)
    def close(self): self._mlflow.end_run()


def make_tracker(backend: str, *, run_dir: str, run_id: str,
                 experiment_name: str, uri: Optional[str]) -> ExperimentTracker:
    backend = (backend or "jsonl").lower()
    if backend == "none":
        return NullTracker()
    if backend == "jsonl":
        return JsonlTracker(run_dir, run_id)
    if backend == "mlflow":
        return MLflowTracker(experiment_name, run_id, uri)
    raise ValueError(f"unknown tracking backend '{backend}' "
                     f"(use jsonl|mlflow|none)")
