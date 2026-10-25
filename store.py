import os, json
import numpy as np
import faiss

INDEX_PATH = "data/index.faiss"
META_PATH = "data/meta.json"

def build_index(vectors):
    arr = np.array(vectors, dtype="float32")
    faiss.normalize_L2(arr)
    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    return index

def save_store(index, meta):
    os.makedirs("data", exist_ok=True)
    faiss.write_index(index, INDEX_PATH + ".tmp")
    with open(META_PATH + ".tmp", "w", encoding="utf-8")as f:
        json.dump(meta, f, ensure_ascii=False)
    os.replace(INDEX_PATH + ".tmp", INDEX_PATH)
    os.replace(META_PATH + ".tmp", META_PATH)

def load_store():
    if not (os.path.exists(INDEX_PATH) and os.path.exists(META_PATH)):
        return None, []
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    if index.ntotal != len(meta):
        raise ValueError(f"Index has {index.ntotal} vectors but meta has {len(meta)} entries. Re-ingest. ")
    return index, meta

def search(index, meta, query_vector, k=4):
    q = np.array([query_vector], dtype="float32")
    faiss.normalize_L2(q)
    scores, ids = index.search(q, k)
    results = []
    for score, i in zip(scores[0], ids[0]):
        if i == -1:
            continue
        results.append({**meta[i], "score": float(score)})
    return results

def remove_document(index, meta, file_name):
    vectores = index.reconstruct_n(0, index.ntotal)
    keep = [i for i, m in enumerate(meta) if m["file_name"] != file_name]
    new_meta = [meta[i] for i in keep]
    new_index = build_index(vectores[keep])
    return new_index, new_meta