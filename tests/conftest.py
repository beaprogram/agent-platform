import importlib.util
import os
import pathlib

os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("SESSIONS_TABLE", "sessions")
os.environ.setdefault("LLM_SECRET_ARN", "llm")
os.environ.setdefault("CHUNKS_TABLE", "chunks")
os.environ.setdefault("EMBEDDINGS_SECRET_ARN", "emb")

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def orch():
    return _load("orchestrator/handler.py", "orch_handler")


@pytest.fixture(scope="session")
def ing():
    return _load("ingestion/handler.py", "ing_handler")
