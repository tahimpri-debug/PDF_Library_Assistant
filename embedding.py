import os, json
from sentence_transformers import SentenceTransformer

CACHE_PATH = "data/cache.json"
QUERY_PREFIX = "Represent this sentence for searching relevent passages: "
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)

def embed_chunks(chunks):
    cache = load_cache()
    new = [c for c in chunks if c["hash"] not in cache]
    print(f"New to embed: {len(new)} (cache hits: {len(chunks ) - len(new)})")
    if new:
        vecs = model.encode([c["text"] for c in new], batch_size=32, normalize_embeddings=True, show_progress_bar=True)

        for c, v in zip(new, vecs):
            cache[c["hash"]] = v.tolist()
        save_cache(cache)
    return [cache[c["hash"]] for c in chunks]

def embed_query(question):
    return model.encode(QUERY_PREFIX + question, normalize_embeddings=True).tolist()
