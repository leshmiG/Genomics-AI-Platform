import pytest

torch = pytest.importorskip("torch")

from app.ml.cohort import make_cohort  # noqa: E402
from app.ml.torch_model import build_model, encode, train  # noqa: E402


def test_encode_shape_and_stats_reuse():
    df = make_cohort(200, 1)
    x, stats = encode(df)
    assert x.shape == (200, 3 + 3 + 5)
    x2, _ = encode(df, stats)
    assert (x == x2).all()


def test_forward_shape():
    m = build_model(11)
    assert m(torch.zeros(4, 11)).shape == (4, 1)


def test_training_beats_chance():
    r = train(epochs=8)
    assert r["metrics"]["auc"] > 0.6
