"""Optional PyTorch tabular MLP for the clopidogrel-response task.

Why it exists: the job description lists TensorFlow/PyTorch. On this small tabular problem the
calibrated logistic regression in ``train.py`` is the production choice (see model card); this
module shows how the same data/preprocessing/evaluation would be done in PyTorch so the
comparison is honest and reproducible.

STATUS: written to be correct but NOT executed in the authoring sandbox (torch could not be
installed there). The CI workflow installs the ``torch`` extra and runs ``tests/test_torch_model.py``.

Run:  pip install -e .[torch] && python -m app.ml.torch_model --out artifacts/torch
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from app.ml.cohort import BINARY, CATEGORICAL, FEATURES, NUMERIC, PHENOTYPES, TARGET, make_cohort

try:  # guarded: the core service must run without torch
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


def require_torch() -> None:
    if torch is None:
        raise RuntimeError("PyTorch is not installed. Install with: pip install -e .[torch]")


def encode(df, stats: dict | None = None) -> tuple[np.ndarray, dict]:
    """Standardise numerics, one-hot the phenotype. ``stats`` from training is reused at inference."""
    if stats is None:
        stats = {c: (float(df[c].mean()), float(df[c].std() or 1.0)) for c in NUMERIC}
    num = np.stack([(df[c].to_numpy(float) - stats[c][0]) / stats[c][1] for c in NUMERIC], axis=1)
    binary = df[BINARY].to_numpy(float)
    onehot = np.stack([(df[CATEGORICAL[0]] == p).to_numpy(float) for p in PHENOTYPES], axis=1)
    return np.concatenate([num, binary, onehot], axis=1).astype("float32"), stats


def build_model(n_in: int, hidden: int = 32, dropout: float = 0.1):
    require_torch()
    return nn.Sequential(
        nn.Linear(n_in, hidden), nn.ReLU(), nn.Dropout(dropout),
        nn.Linear(hidden, hidden // 2), nn.ReLU(),
        nn.Linear(hidden // 2, 1),  # logits; BCEWithLogitsLoss applies the sigmoid
    )


def train(epochs: int = 40, seed: int = 0, lr: float = 1e-3, weight_decay: float = 1e-4) -> dict:
    require_torch()
    from sklearn.metrics import brier_score_loss, roc_auc_score
    from sklearn.model_selection import train_test_split

    torch.manual_seed(seed)
    np.random.seed(seed)
    df = make_cohort(6000, 42)
    tr, te = train_test_split(df, test_size=0.25, random_state=seed, stratify=df[TARGET])
    tr, va = train_test_split(tr, test_size=0.2, random_state=seed, stratify=tr[TARGET])
    xtr, stats = encode(tr)
    xva, _ = encode(va, stats)
    xte, _ = encode(te, stats)
    ytr = torch.tensor(tr[TARGET].to_numpy(), dtype=torch.float32).unsqueeze(1)

    model = build_model(xtr.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.BCEWithLogitsLoss()
    xt = torch.tensor(xtr)
    best, best_state, patience = 1e9, None, 0
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(xt))
        for i in range(0, len(xt), 128):
            idx = perm[i:i + 128]
            opt.zero_grad()
            loss_fn(model(xt[idx]), ytr[idx]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            p = torch.sigmoid(model(torch.tensor(xva))).squeeze(1).numpy()
        val_brier = float(brier_score_loss(va[TARGET], p))
        if val_brier < best - 1e-5:  # early stopping on a proper scoring rule
            best, patience = val_brier, 0
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience += 1
            if patience >= 5:
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        pt = torch.sigmoid(model(torch.tensor(xte))).squeeze(1).numpy()
    return {
        "model": model, "stats": stats,
        "metrics": {"auc": float(roc_auc_score(te[TARGET], pt)),
                    "brier": float(brier_score_loss(te[TARGET], pt)), "val_brier": best},
        "features": FEATURES,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/torch")
    a = ap.parse_args()
    r = train()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    torch.save(r["model"].state_dict(), out / "mlp.pt")
    (out / "card.json").write_text(json.dumps({"metrics": r["metrics"], "stats": r["stats"]}, indent=2))
    print(json.dumps(r["metrics"], indent=2))


if __name__ == "__main__":
    main()
