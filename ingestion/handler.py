import json
import os
import time
import urllib.request
from urllib.parse import unquote_plus

import boto3

CHUNKS_TABLE = os.environ["CHUNKS_TABLE"]
SECRET_ARN = os.environ["EMBEDDINGS_SECRET_ARN"]
EMB_URL = os.environ.get("EMBEDDINGS_API_URL", "https://api.jina.ai/v1/embeddings")
EMB_MODEL = os.environ.get("EMBEDDINGS_MODEL", "jina-embeddings-v3")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "100"))
EMBED_BATCH = 32

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table(CHUNKS_TABLE)
_secrets = boto3.client("secretsmanager")
_api_key = None


def _get_api_key():
    global _api_key
    if _api_key is None:
        _api_key = _secrets.get_secret_value(SecretId=SECRET_ARN)["SecretString"].strip()
    return _api_key


def _chunk(text):
    text = text.strip()
    if not text:
        return []
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + CHUNK_SIZE, n)
        if end < n:
            ws = text.rfind(" ", start, end)
            if ws > start:
                end = ws
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _embed(texts):
    payload = json.dumps(
        {"model": EMB_MODEL, "task": "retrieval.passage", "normalized": True, "input": texts}
    ).encode("utf-8")
    req = urllib.request.Request(
        EMB_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; agent-platform/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [d["embedding"] for d in data["data"]]


def handler(event, context):
    results = []
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = unquote_plus(rec["s3"]["object"]["key"])
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8", "ignore")
        chunks = _chunk(raw)
        if not chunks:
            results.append({"key": key, "chunks": 0})
            continue

        total = 0
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = chunks[i : i + EMBED_BATCH]
            vectors = _embed(batch)
            with table.batch_writer() as bw:
                for offset, (chunk_text, vector) in enumerate(zip(batch, vectors)):
                    bw.put_item(
                        Item={
                            "doc_id": key,
                            "chunk_id": f"{i + offset:05d}",
                            "text": chunk_text,
                            "embedding": json.dumps(vector),
                            "source": key,
                            "created_at": int(time.time()),
                        }
                    )
            total += len(batch)
        results.append({"key": key, "chunks": total})
        print(json.dumps({"ingested_doc": key, "chunks": total}))

    return {"ingested": results}
