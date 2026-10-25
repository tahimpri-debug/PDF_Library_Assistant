import re
import hashlib

SEPARATOR = "\n\n"

def clean_pdf_text(text):
    
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text) 
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def split_long_paragraph(paragraph, max_chars, overlap_chars):
    
    slices = []
    start = 0
    
    while start < len(paragraph):
        end = start + max_chars
        slices.append(paragraph[start:end])
        if end >= len(paragraph):
            break
        start = end - overlap_chars
    return slices

def split_by_sentences(text, max_chars=1000, overlap_chars=150):
    
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current, last = [], "", ""
    
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_long_paragraph(sentence, max_chars, overlap_chars))
            last = ""
            continue

        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current)
            overlap = current[-overlap_chars:].split(" ", 1)[-1]
            if len(overlap) + 1 + len(sentence) > max_chars:
                overlap = ""
            current = (overlap + " " + sentence).strip()
        else:
            current = (current + " " + sentence).strip()
        last = sentence

    if current:
        chunks.append(current)

    return chunks

def recursive_split(text, max_chars=1000, overlap_chars=150):
    
    paragraphs = [p.strip() for p in text.split(SEPARATOR) if p.strip()]
    chunks, current = [], ""

    for para in paragraphs: 
        if len(para) > max_chars:
            if current:
                chunks.append(split_by_sentences(para, max_chars, overlap_chars))
        elif current and len(current) + len(SEPARATOR) + len(para) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = (current + SEPARATOR + para) if current else para
    if current:
        chunks.append(current)
    return chunks

def chunk_pages(pages):
    record = []
    for page in pages:
        text = clean_pdf_text(page["text"])
        index = 0
        for chunk in recursive_split(text):
            if len(chunk) < 30:
                continue
            record.append({
                "file_name": page["file_name"],
                "page": page["page"],
                "text": chunk,
                "hash": hashlib.sha3_256(chunk.encode("utf-8")).hexdigest(),
            })
            index += 1
    
    return record