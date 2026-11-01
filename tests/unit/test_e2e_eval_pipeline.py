"""experiments/e2e/eval_pipeline.py için duman testi: gerçek uygulama/URL açılmaz."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pipeline_runs_on_v1_manifest_without_side_effects(tmp_path: Path) -> None:
    out = subprocess.run(
        [
            sys.executable,
            str(ROOT / "experiments/e2e/eval_pipeline.py"),
            str(ROOT / "datasets/manifests/nlu_dev_v1.jsonl"),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
        env={**os.environ, "VOXFLOW_DATA_DIR": str(tmp_path)},
    )
    rep = json.loads(out.stdout)
    assert rep["n"] == 66
    assert 0.0 <= rep["action_success_rate"] <= 1.0
    assert 0.0 <= rep["intent_accuracy"] <= 1.0
    assert set(rep["per_intent_action_success"]) >= {"create_task", "unsupported", "unknown"}
    assert not list(tmp_path.iterdir())  # bellek içi depo: diske hiçbir şey yazılmadı
