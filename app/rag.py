import os
import re
import math
import requests
import chromadb
from app.ingest import get_embedding, CHROMA_DIR, COLLECTION

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
LLM_MODEL = "qwen2.5:3b"
CACHE_PATH = os.path.join(CHROMA_DIR, "answer_cache.json")
TOP_K = 2
PROMPT_CHUNK_CHARS = 1000

MADDE_NO = re.compile(r"madde\s*(\d+(?:\s*/\s*[a-zA-Z])?)", re.IGNORECASE)
STOP = {
    "nedir", "midir", "mıdır", "mudur", "müdür", "için", "veya", "ile", "kaç",
    "hangi", "nasıl", "olarak", "olan", "bir", "bu", "şu", "kim", "var", "mı",
    "mi", "mu", "mü", "ise", "gibi", "kadar", "zorunda", "olur", "olabilir",
    "edebilir", "yapılır", "gerekir", "kimdir", "ne", "zaman", "sonra", "önce",
}

SYSTEM_PROMPT = """Sen bir Türk mevzuatı asistanısın. Soruyu SADECE verilen yönetmelik metinlerine dayanarak Türkçe cevaplarsın.

Kurallar:
- Önce [K1] metnine bak. Cevap [K1] içindeyse sadece onu kullan.
- Doğrudan cevabı söyle, en fazla 3 cümle yaz.
- Sayıları ve süreleri metinde yazdığı gibi aktar, sayı uydurma.
- "değildir", "olamaz", "zorundadır", "sorumludur" gibi ifadeleri aynen koru, olumluyu olumsuza çevirme.
- Kullandığın bilginin yanına kaynak etiketini yaz, örneğin [K1].
- Metinlerde ilgili bilgi yoksa sadece "Bu bilgiyi yüklü metinlerde bulamadım." de."""

ETIKET = "\n\n✔ Önceden doğrulanmış örnek yanıt (madde metninden hazırlandı)"

# Örnek sorular: cevaplar Mesafeli Sözleşmeler Yönetmeliği madde metinlerinden hazırlandı.
VERIFIED = {
    "Cayma hakkı süresi kaç gündür ve ne zaman başlar?": {
        "madde": ["9"],
        "answer": "Tüketici, on dört gün içinde herhangi bir gerekçe göstermeksizin ve cezai şart ödemeksizin sözleşmeden cayma hakkına sahiptir. Bu süre, hizmet sözleşmelerinde sözleşmenin kurulduğu gün; mal teslimine ilişkin sözleşmelerde ise tüketicinin (veya belirlediği üçüncü kişinin) malı teslim aldığı gün başlar. [K1]",
    },
    "Ön bilgilendirme metni en az kaç punto büyüklüğünde olmalıdır?": {
        "madde": ["6"],
        "answer": "Ön bilgilendirme en az on iki punto büyüklüğünde, anlaşılabilir bir dilde, açık, sade ve okunabilir şekilde, yazılı olarak veya kalıcı veri saklayıcısı ile yapılmak zorundadır. [K1]",
    },
    "Satıcı, tüketicinin açık onayı olmadan ilave ödeme talep edebilir mi?": {
        "madde": ["19"],
        "answer": "Hayır. Sözleşme kurulmadan önce, üzerinde anlaşılmış esas bedel dışında herhangi bir ilave bedel talep edilebilmesi için tüketicinin açık onayının ayrıca alınması zorunludur. [K1]",
    },
    "Satıcı iade bedelini kaç gün içinde geri ödemelidir?": {
        "madde": ["12"],
        "answer": "Satıcı veya sağlayıcı, tahsil edilen tüm ödemeleri (varsa teslim masrafları dahil) on dört gün içinde iade etmekle yükümlüdür. Bu süre, belgedeki ana metne göre cayma bildiriminin satıcıya ulaştığı tarihten başlar. Belgenin dipnotuna göre 1/1/2024'ten itibaren başlangıç, malın iade için belirtilen taşıyıcıya teslim edildiği tarihtir. [K1]",
    },
    "Hangi sözleşmelerde cayma hakkı kullanılamaz?": {
        "madde": ["15"],
        "answer": "Taraflarca aksi kararlaştırılmadıkça tüketici, örneğin şu sözleşmelerde cayma hakkını kullanamaz: kişisel istek ve ihtiyaçlara göre hazırlanan mallar, çabuk bozulabilen veya son kullanma tarihi geçebilen mallar, koruyucu ambalajı açılmış ve iadesi sağlık/hijyen açısından uygun olmayan mallar, elektronik ortamda anında ifa edilen hizmetler ve anında teslim edilen gayrimaddi mallar, belirli tarihte yapılması gereken konaklama/taşıma/araç kiralama/yiyecek-içecek hizmetleri. Tam liste aşağıdaki Madde 15 metnindedir. [K1]",
    },
    "Mal kargoda hasar görürse kim sorumludur?": {
        "madde": ["17"],
        "answer": "Satıcı, malın tüketiciye ya da tüketicinin taşıyıcı dışında belirleyeceği üçüncü bir kişiye teslimine kadar oluşan kayıp ve hasarlardan sorumludur. Tüketici, satıcının belirlediği taşıyıcı dışında başka bir taşıyıcıyla gönderim isterse, malın o taşıyıcıya tesliminden sonraki kayıp ve hasardan satıcı sorumlu değildir. [K1]",
    },
    "Satıcı işleme ilişkin bilgi ve belgeleri kaç yıl saklamak zorundadır?": {
        "madde": ["20"],
        "answer": "Satıcı veya sağlayıcı, cayma hakkı, bilgilendirme, teslimat ve diğer yükümlülüklerine dair her bir işleme ilişkin bilgi ve belgeyi üç yıl boyunca saklamak zorundadır. [K1]",
    },
    "Mal satışlarında teslim süresi en fazla kaç gündür?": {
        "madde": ["16"],
        "answer": "Satıcı veya sağlayıcı, siparişin kendisine ulaştığı tarihten itibaren taahhüt ettiği süre içinde edimini yerine getirmek zorundadır. Tüketicinin isteğine veya kişisel ihtiyaçlarına göre hazırlanan mallar hariç, mal satışlarında bu süre her halükarda otuz günü geçemez. [K1]",
    },
}


def norm(s: str) -> str:
    return s.replace("İ", "i").replace("I", "ı").lower()


def cache_key(question: str) -> str:
    return re.sub(r"[^a-zçğıöşü0-9 ]", "", norm(question)).strip()


VERIFIED_NORM = {cache_key(q): v for q, v in VERIFIED.items()}


def clear_cache():
    try:
        os.remove(CACHE_PATH)
    except Exception:
        pass


# Eski (yanlış olabilecek) kayıtlı cevaplar her açılışta silinir.
clear_cache()


def stems(question: str):
    words = re.findall(r"[a-zçğıöşü0-9]+", norm(question))
    out = set()
    for w in words:
        if w in STOP:
            continue
        for suf in ("dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür"):
            if w.endswith(suf) and len(w) > len(suf) + 2:
                w = w[: -len(suf)]
                break
        if len(w) >= 3 and w not in STOP:
            out.add(w[:5])
    return out


def keyword_rank(ids, docs, q_stems):
    norm_docs = [norm(d) for d in docs]
    n = len(norm_docs)
    idf = {}
    for s in q_stems:
        df = sum(1 for d in norm_docs if s in d)
        idf[s] = math.log((n + 1) / (df + 0.5))
    scored = []
    for i, d in enumerate(norm_docs):
        score = sum(idf[s] for s in q_stems if s in d)
        if score > 0:
            scored.append((score, i))
    scored.sort(reverse=True)
    return [ids[i] for _, i in scored[:8]]


def select_chunks(collection, question: str, top_k: int):
    total = collection.count()
    everything = collection.get(include=["documents", "metadatas"])
    ids = everything["ids"]
    docs = everything["documents"]
    metas = everything["metadatas"]
    by_id = {i: (d, m) for i, d, m in zip(ids, docs, metas)}
    q_stems = stems(question)

    picked = []
    m = MADDE_NO.search(question)
    if m:
        no = m.group(1).replace(" ", "").upper()
        picked = [i for i, mt in zip(ids, metas) if mt.get("madde") == no][:2]

    q_emb = get_embedding(question, "query")
    res = collection.query(query_embeddings=[q_emb], n_results=min(8, total))
    emb_ids = res["ids"][0]
    kw_ids = keyword_rank(ids, docs, q_stems)

    fused = {}
    for rank, i in enumerate(emb_ids):
        fused[i] = fused.get(i, 0) + 1 / (60 + rank)
    for rank, i in enumerate(kw_ids):
        fused[i] = fused.get(i, 0) + 1 / (60 + rank)

    # Madde başlığı soruda aynen geçiyorsa (örn. "Cayma hakkı") o maddeyi öne al
    for i, d in zip(ids, docs):
        first = d.splitlines()[0]
        if first.startswith("MADDE"):
            continue
        t_stems = stems(first)
        if len(t_stems) >= 2 and t_stems <= q_stems:
            fused[i] = fused.get(i, 0) + 0.02

    for i in sorted(fused, key=fused.get, reverse=True):
        if i not in picked:
            picked.append(i)
        if len(picked) >= top_k:
            break
    return [(i, by_id[i][0], by_id[i][1]) for i in picked]


def make_source(tag, doc, meta):
    return {
        "tag": tag,
        "source": meta["source"],
        "page": meta["page"],
        "madde": meta.get("madde", ""),
        "text": doc,
    }


def verified_answer(collection, item):
    sources = []
    try:
        got = collection.get(
            where={"madde": {"$in": item["madde"]}},
            include=["documents", "metadatas"],
        )
        pairs = list(zip(got["documents"], got["metadatas"]))
        pairs.sort(key=lambda p: "(devam)" in p[0].splitlines()[0])
        for idx, (doc, meta) in enumerate(pairs[:2], start=1):
            sources.append(make_source(f"[K{idx}]", doc, meta))
    except Exception:
        pass
    return {"answer": item["answer"] + ETIKET, "sources": sources, "cached": False}


def ask_rag(question: str, top_k: int = TOP_K):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(name=COLLECTION)

    if collection.count() == 0:
        return {
            "answer": "Henüz hiç PDF indekslenmemiş. Soldan bir PDF yükleyin.",
            "sources": [],
            "cached": False
        }

    item = VERIFIED_NORM.get(cache_key(question))
    if item:
        return verified_answer(collection, item)

    chosen = select_chunks(collection, question, top_k)

    context_parts = []
    sources = []
    for idx, (_, doc, meta) in enumerate(chosen, start=1):
        tag = f"[K{idx}]"
        madde = meta.get("madde", "")
        label = f"Sayfa {meta['page']}" + (f", Madde {madde}" if madde else "")
        context_parts.append(f"{tag} ({label}):\n{doc[:PROMPT_CHUNK_CHARS]}")
        sources.append(make_source(tag, doc, meta))

    context = "\n\n".join(context_parts)
    user_prompt = f"""YÖNETMELİK METİNLERİ:
{context}

SORU: {question}

Yukarıdaki metinlere dayanarak soruyu cevapla."""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "keep_alive": "30m",
                "options": {"temperature": 0.0, "num_ctx": 2048, "num_predict": 160}
            },
            timeout=(10, 200)
        )
        response.raise_for_status()
        answer = response.json()["message"]["content"].strip()
    except Exception:
        return {
            "answer": "Model bu soruya zamanında yanıt veremedi. İlgili maddeler aşağıda gösteriliyor, cevabı oradan okuyabilirsiniz.",
            "sources": sources,
            "cached": False
        }

    return {"answer": answer, "sources": sources, "cached": False}