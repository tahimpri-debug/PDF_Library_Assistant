# PDF Library Assistant

A command-line assistant that reads a folder of PDFs and answers questions with citations like `ml_survey.pdf, page 7`. It saves its index between runs, never embeds the same text twice, and refuses to answer when nothing relevant is found (without calling the LLM).

Built in plain Python, with no LangChain or LlamaIndex.

## How it works

```
PDFs -> pages -> chunks -> embeddings -> FAISS index
                                              |
question -> embedding -> top-k search -> score check -> prompt -> LLM -> answer + sources
```

| Part | Choice |
|---|---|
| PDF reading | `pypdf`, page by page |
| Chunking | Own recursive splitter: paragraphs, then sentences, then characters (about 1000 characters, 150 overlap) |
| Embeddings | `BAAI/bge-small-en-v1.5` (384 dimensions, free, runs locally) |
| Vector store | FAISS `IndexFlatIP` with normalized vectors (inner product = cosine similarity) |
| Metadata | `data/meta.json` (file name, page, text, hash for each chunk) |
| Cache | `data/cache.json`, keyed by the hash of the chunk text |
| LLM | Groq chat completions endpoint, called with `requests.post` |

## Features

- Page-by-page PDF reading. Pages with no text (scanned) are skipped with a warning.
- Every chunk keeps its `chunk_id`, file name, page number, text and hash.
- Embedding cache: ingesting unchanged PDFs again makes zero new embeddings.
- The index and metadata files are saved safely (written to `.tmp` files first), and their sizes are checked on startup.
- Score threshold: if the best match is below the threshold, the app answers "Not found in your documents" and makes no LLM call.
- Numbered sources in the prompt. The answer cites `[1]`, `[2]`, and the file and page are printed after it.
- Menu: ingest, ask, list documents, remove a document, exit.
- Friendly messages for no internet, bad API key (401) and rate limit (429).

## Setup

Python 3.10 or newer.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install the libraries
pip install -r requirements.txt

# 3. Create your .env file
cp .env.example .env            # then open .env and add your key

# 4. Put your PDFs in the pdfs/ folder

# 5. Run
python app.py
```

The first run downloads the embedding model (about 130 MB). After that it works offline, except for the LLM call.

### `.env` file

```
GROQ_API_KEY=your_key_here
BASE_URL=https://api.groq.com/openai/v1
MODEL_NAME=your_model_name
```

The `.env` file is in `.gitignore` and is never committed. Only `.env.example` is.

## Usage

```
========================================
1. Ingest ./pdfs
2. Ask
3. List Documents
4. Remove document
5. Exit
========================================
```

1. Choose **1** once to read, chunk, embed and index your PDFs.
2. Choose **2** and type a question.
3. Choose **3** to see which documents are indexed and how many chunks each has.
4. Choose **4** to remove a document. The index is rebuilt without its chunks.

## Example run

Replace this with a real run from your own PDFs.

```
Choose: 1
Found 3 PDFs ... -> ... chunks. New to embed: ... (cache hits: 0)
Index saved (... vectors).

Choose: 2
Question: <your question>

Answer: <answer with citations like [1]>

Sources:
[1] <file>.pdf, page <n> (score 0.xx)
[2] <file>.pdf, page <n> (score 0.xx)

Choose: 2
Question: <an unrelated question>
Not found in your documents.
```

## Project structure

```
pdf_library/
  app.py          menu, PDF loading, ask flow, LLM call, prompt
  chunker.py      cleaning and recursive splitter, plus its tests
  embedding.py    local embeddings with a hash cache
  store.py        FAISS index and metadata: build, save, load, search, remove
  pdfs/           your PDFs (not committed)
  data/           index.faiss, meta.json, cache.json (not committed)
  requirements.txt, .env.example, .gitignore, README.md
```

## Testing

Run the chunker tests:

```bash
python chunker.py
```

Manual checks I ran:

- [ ] A question that only PDF 2 can answer: the citation names PDF 2.
- [ ] An unrelated question: refused, no LLM call.
- [ ] Ingesting again with no changes: 0 new embeddings.
- [ ] Removing a document, then asking about it: not found.
- [ ] A scanned (image-only) PDF: a warning, no crash.
- [ ] Wrong API key, no internet: a friendly message each time.

## Choosing the threshold

I printed the top score for questions the PDFs can answer and for unrelated ones, then chose a value between the two groups. Fill in your numbers:

| Question type | Top scores seen |
|---|---|
| Answerable | ... |
| Unrelated | ... |

Threshold used: `...`

## What I learned

- FAISS stores only vectors. The text, file name and page live in a separate metadata file, and the two must always have the same number of entries. If they get out of sync, a search result points to the wrong text and the citations are wrong.
- Vectors from different embedding models cannot be compared, so changing the model means deleting `data/` and ingesting again.
- A score threshold is better chosen from printed scores than guessed.
- Caching embeddings by text hash makes repeated ingestion fast and free.
- Writing to a `.tmp` file and then replacing the real file protects the index if the program stops halfway.
- Add your own lessons here.

## Known limits

- Scanned PDFs have no text and are skipped (no OCR).
- The sentence splitter can split after abbreviations such as "et al." or "Fig. 3".
- `IndexFlatIP` checks every vector, which is fine for hundreds of pages but gets slow for very large libraries.
- The embedding model is English-focused.
