# ReguRAG: Akıllı Risk ve Mevzuat Asistanı

Yüklenen mevzuat PDF'lerine soru soran, cevabı **kaynak maddeyle birlikte** gösteren, **tamamen yerel çalışan** bir RAG (Retrieval-Augmented Generation) asistanı.

**Hazırlayan:** Kerim KÖK

## Ne yapar?

Şirket çalışanlarının uzun mevzuat metinleri arasında manuel arama yaparken kaybettiği zamanı azaltır. Kullanıcı "Cayma hakkı süresi kaç gündür?" gibi bir soru sorar; sistem ilgili maddeyi bulur, cevabı üretir ve cevabın altında kaynak madde metnini gösterir. Böylece kullanıcı cevabı kaynaktan doğrulayabilir.

Örnek belge olarak **Mesafeli Sözleşmeler Yönetmeliği** kullanılmıştır. Arayüzden kendi PDF belgenizi de yükleyebilirsiniz.

## Özellikler

- **Tamamen yerel:** Yapay zekâ modeli (Ollama) kendi bilgisayarınızda çalışır. Belgeler ve sorular dışarı çıkmaz, dış yapay zekâ servisi kullanılmaz.
- **Kaynak gösterir:** Her cevabın altında ilgili madde metni, sayfa ve madde numarası görünür.
- **Madde bazlı parçalama:** PDF, maddelere göre bölünür. Üst/alt bilgiler ve dipnotlar temizlenir.
- **Hibrit arama:** Anlamsal (vektör) arama ile anahtar kelime aramasını birleştirir.
- **PDF yükleme:** Arayüzden yeni PDF eklenip aynı anda sorgulanabilir.
- **Örnek soru butonları:** Standlarda ve sunumlarda tek tıkla kullanım için.
- **REST API:** FastAPI ile `/ask`, `/upload`, `/files` uç noktaları. API dokümantasyonu: `http://localhost:8000/docs`

## Mimari

```
PDF belgesi
   │
   ▼
Madde madde parçalama ──► Embedding (nomic-embed-text) ──► ChromaDB
                                                              │
Kullanıcı sorusu ──► Hibrit arama (vektör + anahtar kelime) ◄─┘
                              │
                              ▼
                     En ilgili maddeler
                              │
                              ▼
                  Yerel LLM (qwen2.5:3b)
                              │
                              ▼
              Cevap + kaynak madde metni
```

## Teknolojiler

| Bileşen | Kullanılan |
|---|---|
| API | FastAPI + Uvicorn |
| Vektör veritabanı | ChromaDB |
| Embedding modeli | nomic-embed-text (Ollama) |
| Dil modeli | qwen2.5:3b (Ollama) |
| PDF okuma | pypdf |
| Arayüz | Tek dosya HTML/JS |
| Çalıştırma | Docker Compose |

## Kurulum

**Gereksinimler:** Docker Desktop ve Ollama kurulu ve açık olmalı. GPU gerekmez, yaklaşık 8 GB RAM yeterlidir.

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

PDF belgenizi `data/` klasörüne koyun, sonra:

```bash
docker compose up --build
```

Tarayıcıda `http://localhost:8000` adresini açın. İlk açılışta PDF indekslenir (1-3 dakika). Yeni bir PDF'i baştan indekslemek için `chroma_db` klasörünün içini silip yeniden başlatın.

## Proje yapısı

```
app/
  main.py       FastAPI uç noktaları
  ingest.py     PDF okuma, temizleme, madde bazlı parçalama, indeksleme
  rag.py        Arama, prompt ve cevap üretimi
  index.html    Sohbet ve PDF yükleme arayüzü
data/           PDF belgeleri
chroma_db/      Vektör veritabanı (otomatik oluşur)
docker-compose.yml
Dockerfile
requirements.txt
```

## Örnek sorular

- Cayma hakkı süresi kaç gündür ve ne zaman başlar?
- Ön bilgilendirme metni en az kaç punto büyüklüğünde olmalıdır?
- Satıcı, tüketicinin açık onayı olmadan ilave ödeme talep edebilir mi?
- Mal kargoda hasar görürse kim sorumludur?

Arayüzdeki örnek soru butonlarının cevapları, yönetmelik madde metinlerinden önceden hazırlanmıştır ve cevabın sonunda "Önceden doğrulanmış örnek yanıt" etiketiyle belirtilir. Serbest yazılan sorular yerel model tarafından üretilir.

## Sınırlamalar

- **Küçük model:** `qwen2.5:3b` Türkçe hukuk metinlerinde zaman zaman hata yapabilir (örneğin olumlu cümleyi olumsuza çevirmek, yanlış maddeyi karıştırmak). Bu nedenle her cevabın altında kaynak madde gösterilir ve kullanıcının doğrulaması önerilir.
- **Dipnotlar dışarıda:** PDF'teki değişiklik dipnotları (ör. 2024'te yürürlüğe giren değişiklikler) arama dışında bırakılmıştır. Bazı maddelerin güncel hali bu nedenle yanıtlara yansımayabilir.
- **Ölçüm yok:** Sistemin doğruluğu henüz geniş bir test setiyle ölçülmemiştir.
- **Hız:** CPU üzerinde bir cevap 1-3 dakika sürebilir. GPU ile belirgin şekilde kısalır.
- **Güvenlik:** Kimlik doğrulama ve HTTPS yoktur. Yerel demo amaçlıdır.
- **Belge türü:** Madde yapısı (MADDE 1 – ...) olan mevzuat PDF'lerinde en iyi sonucu verir. Farklı yapıdaki belgelerde parçalama daha basit çalışır.

## Gelecek çalışmalar

- Daha büyük model veya GPU desteği
- Soru-cevap doğruluğunu ölçen bir test seti
- Şirkete özel iç prosedür belgelerinin eklenmesi
- Kişisel veri (TCKN, IBAN) maskeleme