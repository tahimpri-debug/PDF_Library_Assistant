import requests
import os
import re
from dotenv import load_dotenv
from pypdf import PdfReader
from chunker import chunk_pages
from embedding import embed_chunks, embed_query
from store import build_index, save_store, load_store, search, remove_document
load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
base_url = os.environ.get("BSE_URL")
ai_model_name = os.environ.get("MODEL_NAME")
THRESHOLD = 0.5

if not api_key:
    print("There are no API key...")
    exit()


def load_pdfs(folder="pdfs"):
    pages = []
    
    if not os.path.isdir(folder):
        print(f"Folder not found : {folder}")
        return pages

    for file_name in sorted(os.listdir(folder)):
        if not file_name.lower().endswith(".pdf"):
            continue
        path = os.path.join(folder, file_name)
        try:
            reader = PdfReader(path)
        except Exception as e:
            print(f"Warning: cannot open {file_name}: {e}")
            continue

        for page_number, page in enumerate(reader.pages, start=1):
            try:
                raw_text = page.extract_text() or ""
            except Exception as e:
                print(f"Warning: {file_name} page {page_number} could not be read: {e}")
                continue
            text = raw_text.strip()
            if not text:
                print(f"Warning: {file_name} page {page_number} has no text (scanned?)")
                continue
            pages.append({
                "file_name": file_name,
                "page": page_number,
                "text": text,
            })
    return pages

def ingest(): 
    pages = load_pdfs("pdfs")
    chunks = chunk_pages(pages)
    vectores = embed_chunks(chunks)
    index = build_index(vectores)
    save_store(index, chunks)
    print(f"Index saved ({index.ntotal} vectors).")

def call_llm(prompt):
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": ai_model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    try:
        respones = requests.post(url, headers=headers, json=body, timeout=60)
        if respones.status_code == 200:
            return respones.json()["choices"][0]["message"]["content"].strip()
        if respones.status_code == 401:
            print("Bad API key (401). Check your .env.")
            return None
        if respones.status_code == 429:
            print("Rate limit or no credit (429). Try again later.")
            return None
        print("LLM error. Status code ", respones.status_code)
        print(respones.text)

        return None
    
    except requests.exceptions.RequestException:
        print("Could not connect to the API. Check you internet")
        return None
    except(KeyError, IndexError, ValueError):
        print("Unexpeted respones from the API")
        return None

def build_prompt(question, results):
    sources = []
    
    for i,r in enumerate(results, start=1):
        sources.append(f"[{i}] ({r['file_name']}, page {r['page']})\n{r['text']}")
    context = "\n\n".join(sources)
    return(
        "Answer the question using only the sources below. "
        "Cite sources like [1] or [2]. "
        "If the sources do not contain the answer, say: not found in your documents.\n\n"
        f"Sources:\n{context}\n\n"
        f"Question: {question}"
    )

def ask(question, k=4):
    index, meta = load_store()
    
    if index is None:
        print("No index yet. Run ingest first.")
        return
    results = search(index, meta, embed_query(question), k)
    if not results or results[0]["score"] < THRESHOLD:
        print("Not found in your documents.")
        return
    answer = call_llm(build_prompt(question, results))
    if answer:
        print("\nAnswer:", answer)
        print("\nSources:")
        for i, r in enumerate(results, start=1):
            print(f"[{i}] {r['file_name']}, page {r['page']} (score {r['score']:.2f})")

def list_document():
    index, meta = load_store()
    
    if index is None:
        print("No index yet. Run ingest first. ")
        return
    count = {}
    for m in meta:
        count[m["file_name"]] = count.get(m["file_name"], 0) + 1
    for name, n in count.items():
        print(f"{name}: {n} chunks")

def remove_doc():
    index, meta = load_store()
    
    if index is None:
        print("No index yet. Run ingest first.")
        return
    names = sorted({m["file_name"] for m in meta})
    for i, name in enumerate(names, start=1):
        print(f"{i}. {name}")
    choice = input("Number of the file to remove: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(names)):
        print("Please type a number from the list.")
        return
    
    name = names[int(choice) - 1]
    index, meta = remove_document(index, meta, name)
    save_store(index, meta)
    print(f"Removed {name}. {index.ntotal} vectors left.")


if __name__ == "__main__":

    while True:
        print("="*40)
        print("\n1. Ingest ./pdfs")
        print("2. Ask")
        print("3. List Documetns")
        print("4. Remove document")
        print("5. Exit\n")
        print("="*40)

        choice = input("Enter Your Choice : ").strip()

        if choice == "1":
            ingest()
        elif choice == "2":
            question = input("Question : ").strip()
            if question:
                ask(question)
            else:
                print("Please type a quesiton.")
        elif choice == "3":
            list_document()
        elif choice == "4":
            remove_doc()
        elif choice == "5":
            print("Quiting....")
            break
        else:
            print("Please choose 1 to 5.")