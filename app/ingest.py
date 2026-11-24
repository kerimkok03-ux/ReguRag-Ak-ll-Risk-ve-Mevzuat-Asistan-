import os
import re
import bisect
import uuid
import requests
import chromadb
from pypdf import PdfReader

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
DATA_DIR = "/app/data"
CHROMA_DIR = "/app/chroma_db"
EMBED_MODEL = "nomic-embed-text"
COLLECTION = "mevzuat_rag"

PAGE_NO = re.compile(r"^[-–]\s*\d+\s*[-–]$")
BOLUM = re.compile(r"^(BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|ALTINCI|YEDİNCİ)\s+BÖLÜM$")
FOOTNOTE_START = re.compile(r"^\(\d\)\s+(Bu değişiklik|\d{1,2}/\d{1,2}/\d{4}\s+tarihli)")
AMEND_TAG = re.compile(r"\((?:Ek|Değişik)[^)]*?RG[^)]*\)(?:\(\d\))*")
MADDE_RE = re.compile(r"^MADDE\s+(\d+(?:/[A-Z])?)\s*[–−-]", re.MULTILINE)


def get_embedding(text: str, kind: str = "document"):
    prefix = "search_query: " if kind == "query" else "search_document: "
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": prefix + text},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["embedding"]


def read_pdf_text(pdf_path: str):
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        raw = AMEND_TAG.sub("", raw)
        pages.append([ln.strip() for ln in raw.splitlines() if ln.strip()])

    counts = {}
    for lines in pages:
        for ln in set(lines):
            counts[ln] = counts.get(ln, 0) + 1
    repeated = set()
    if len(pages) >= 4:
        repeated = {ln for ln, c in counts.items() if c >= 3 and len(ln) <= 60}

    text = ""
    marks = []
    stop = False
    for page_num, lines in enumerate(pages, start=1):
        skip_next = False
        for ln in lines:
            if FOOTNOTE_START.match(ln):
                stop = True
                break
            if skip_next:
                skip_next = False
                continue
            if PAGE_NO.match(ln) or ln in repeated:
                continue
            if BOLUM.match(ln):
                skip_next = True
                continue
            marks.append((len(text), page_num))
            text += ln + "\n"
        if stop:
            break
    return text, marks


def _heading_start(text: str, pos: int):
    prev_end = pos - 1
    if prev_end <= 0:
        return pos
    prev_start = text.rfind("\n", 0, prev_end) + 1
    line = text[prev_start:prev_end].strip()
    if line and len(line) <= 60 and not line.endswith((".", ",", ";", ":")):
        return prev_start
    return pos


def _split_long(body: str, label: str, max_len: int):
    parts = []
    while len(body) > max_len:
        cut = body.rfind("\n(", 0, max_len)
        if cut < 300:
            cut = body.rfind("\n", 0, max_len)
        if cut < 300:
            cut = max_len
        parts.append(body[:cut].strip())
        body = body[cut:].strip()
        if label:
            body = f"{label} (devam)\n{body}"
    parts.append(body.strip())
    return parts


def build_chunks(text: str, marks, max_len: int = 1300):
    starts = [pos for pos, _ in marks]

    def page_at(pos):
        i = bisect.bisect_right(starts, pos) - 1
        return marks[max(i, 0)][1] if marks else 1

    matches = list(MADDE_RE.finditer(text))
    chunks = []
    if not matches:
        for part in _split_long(text, "", max_len):
            if len(part) > 30:
                chunks.append((part, page_at(0), ""))
        return chunks

    bounds = [_heading_start(text, m.start()) for m in matches]
    pre = text[:bounds[0]].strip()
    if len(pre) > 30:
        chunks.append((pre, page_at(0), ""))

    for i, m in enumerate(matches):
        end = bounds[i + 1] if i + 1 < len(matches) else len(text)
        body = text[bounds[i]:end].strip()
        no = m.group(1)
        for part in _split_long(body, f"MADDE {no}", max_len):
            if len(part) > 30:
                chunks.append((part, page_at(m.start()), no))
    return chunks


def ingest_pdf(pdf_path: str, pdf_name: str):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name=COLLECTION)

    try:
        collection.delete(where={"source": pdf_name})
    except Exception:
        pass

    text, marks = read_pdf_text(pdf_path)
    chunks = build_chunks(text, marks)

    for chunk_text, page_num, madde in chunks:
        collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[get_embedding(chunk_text, "document")],
            documents=[chunk_text],
            metadatas=[{"source": pdf_name, "page": page_num, "madde": madde}]
        )
    print(f"{pdf_name} islendi. Eklenen parca: {len(chunks)}")
    return len(chunks)


def run_ingest():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name=COLLECTION)
    if collection.count() > 0:
        print(f"ChromaDB zaten dolu ({collection.count()} parca). Indeksleme atlandi.")
        return

    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    for pdf_name in pdf_files:
        ingest_pdf(os.path.join(DATA_DIR, pdf_name), pdf_name)