import json

import numpy as np
import pytest

from backend.config import DATA
from backend.rag.retriever import Retriever
from backend.rag.store import IndexMismatch, NumpyStore

DQ = json.loads((DATA / "demo_questions.json").read_text(encoding="utf-8"))
CASES = [(f["fault_id"], lang, f[lang]) for f in DQ["faults"] for lang in ("te", "hi", "en")]


@pytest.fixture(scope="module")
async def retriever(tmp_path_factory):
    r = Retriever(index_dir=tmp_path_factory.mktemp("index"))
    await r.ensure(None, force=True)
    return r


@pytest.mark.parametrize("fault,lang,question", CASES)
async def test_demo_questions_hit_right_guide(retriever, fault, lang, question):
    res = await retriever.search(question)
    assert res.fault_id == fault
    assert res.confidence >= 0.5
    assert retriever.guide(fault, lang).language == lang


@pytest.mark.parametrize("q", ["Do you deliver to Chennai?", "Tell me a joke", "How do I change my Instagram password?"])
async def test_unrelated_low_confidence(retriever, q):
    assert (await retriever.search(q)).confidence < 0.5


def test_index_refuses_embedding_model_mismatch(tmp_path):
    st = NumpyStore("hash:char3-5:v1")
    st.add(np.ones((2, 4)), [{"id": "a"}, {"id": "b"}])
    st.save(tmp_path)
    with pytest.raises(IndexMismatch):
        NumpyStore.load(tmp_path, "gemini:text-embedding-x", file_model="hash:char3-5:v1")
    assert len(NumpyStore.load(tmp_path, "hash:char3-5:v1").metas) == 2


async def test_metadata_filter(retriever):
    res = await retriever.search("upper thread keeps breaking", machine_model="RRR STAR (28/48)")
    assert res.fault_id == "upper_thread_breaking"  # guides are machine_model ALL, so still match
