import pytest

from app.ml.train import train


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("models")
    train(n=2500, seed=7, out_dir=d)
    return d
