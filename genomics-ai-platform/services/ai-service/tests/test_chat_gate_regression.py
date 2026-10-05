"""Regression: conversation history must not let off-topic questions bypass the grounding gate."""

import pytest

from app.chat.llm import ExtractiveLLM
from app.chat.service import ChatService
from app.core.config import Settings
from app.rag.ingest import ingest, load_retriever


@pytest.fixture()
def service(tmp_path):
    s = Settings(index_dir=str(tmp_path))
    ingest(s)
    return ChatService(load_retriever(s), ExtractiveLLM(), s)


def test_off_topic_after_on_topic_turn_is_still_refused(service):
    assert service.answer("What is a diplotype?", "same").grounded
    r = service.answer("best pizza recipe in Rome", "same")
    assert not r.grounded and "no_evidence" in r.flags


def test_genuine_followup_still_works(service):
    service.answer("What is TPMT and azathioprine?", "fu")
    assert service.answer("and why does phase matter?", "fu").grounded
