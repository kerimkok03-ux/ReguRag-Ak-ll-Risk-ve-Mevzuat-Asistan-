# 🛡️ ReguRAG: Akıllı Risk ve Mevzuat Asistanı

**ReguRAG**, e-ticaret, fintek ve müşteri hizmetleri ekiplerinin uzun mevzuat metinleri arasında manuel arama yaparken kaybettiği zamanı azaltmak için geliştirilmiş, **%100 yerel çalışan RAG (Retrieval-Augmented Generation)** tabanlı bir mevzuat soru-cevap asistanıdır.

İade, cayma hakkı, ek ücret ve itiraz (chargeback) gibi süreçlerdeki soruları yanıtlar ve cevabın **hangi mevzuat maddesinden alındığını kaynak göstererek (`[K1]`)** kanıtlar.

---

## ✨ Temel Özellikler

* **%100 Yerel ve Gizlilik Odaklı:** Vektör veritabanı (`ChromaDB`), anlamsal arama (`bge-m3`) ve dil modeli (**Ollama / `qwen2.5:3b`**) tamamen yerel olarak çalışır; belgeler ve sorular kesinlikle şirket dışına çıkmaz.
* **Kaynak Kanıtlı Cevaplar:** Cevaplar yalnızca yüklenen belgelere dayandırılır. Her cevabın sonunda ilgili kaynak etiketi (`[K1]`) ve madde metni gösterilerek halüsinasyon riski azaltılır.
* **Madde Bazlı Parçalama:** Mevzuat PDF'leri yapısını bozmadan madde madde parçalanarak indekslenir.
* **Dinamik PDF Yükleme:** Örnek belge olarak *Mesafeli Sözleşmeler Yönetmeliği* kullanılmıştır. Kullanıcılar arayüzden kendi PDF belgelerini yükleyerek asistanı farklı mevzuat ve iç prosedürlerle anında kullanabilir.

---

## 🎯 Hedef Sektör ve Kullanım Alanları

* **E-Ticaret & Fintek Firmaları:** Mesafeli satış mevzuatına hızlı uyum.
* **Müşteri Hizmetleri & İade/İtiraz (Chargeback) Ekipleri:** Müşteri taleplerine mevzuata uygun, hatasız dönüş yapma.
* **Hukuk & Uyum Birimleri:** Yeni çalışanların mevzuata hızlı adaptasyonu ve insan kaynaklı hataların azaltılması.

---

## 🛠️ Teknoloji Yığını

* **Backend:** Python, FastAPI
* **Vektör Veritabanı:** ChromaDB (Yerel)
* **Embedding Modeli:** `bge-m3` (Ollama)
* **Yerel Dil Modeli (LLM):** `qwen2.5:3b` (Ollama)
* **Altyapı:** Docker & Docker Compose
* **Arayüz:** HTML / CSS / JavaScript

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* [Ollama](https://ollama.com/)

### 1. Projeyi Klonlayın
```bash
git clone [https://github.com/kerimkok03-ux/ReguRag-Ak-ll-Risk-ve-Mevzuat-Asistan-.git](https://github.com/kerimkok03-ux/ReguRag-Ak-ll-Risk-ve-Mevzuat-Asistan-.git)
cd ReguRag-Ak-ll-Risk-ve-Mevzuat-Asistan-
