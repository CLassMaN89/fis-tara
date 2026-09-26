# Fiş Tarayıcı v5 — PaddleOCR

Bu sürüm Tesseract.js yerine **PP-OCRv5 server detection + recognition** kullanır. Frontend statik kalır; OCR ayrı bir Python servisinde çalışır.

## Neden iki parça?
PaddleOCR server modeli büyük bir Python inference servisidir. Statik Vercel `index.html` içinde çalıştırılmaz. `server.py` bir container/VM üzerinde çalışır.

## Backend'i çalıştır

Docker:
```bash
docker build -t fis-ocr .
docker run --rm -p 8080:8080 fis-ocr
```

İlk açılışta PaddleOCR model ağırlıkları indirilir.

Test:
```bash
curl http://localhost:8080/health
curl -F "image=@fis.jpg" http://localhost:8080/ocr
```

## Frontend'i bağla

Backend başka domaindeyse `index.html` içindeki:
```js
fetch('/api/ocr'
```
satırını:
```js
fetch('https://SENIN-OCR-SERVISIN/ocr'
```
olarak değiştir.

Aynı domain reverse proxy kullanıyorsan `/api/ocr` bırakılabilir.

## Beklenen JSON
```json
{
  "receipt": {
    "merchant": "MAYÇO",
    "date": "13.09.2026",
    "time": "16:23",
    "receipt_no": "0038",
    "vat": 61.82,
    "total": 680.00,
    "payment": "Kart"
  }
}
```

Not: PaddleOCR açık kaynak modeldir; fakat onu internette 7/24 çalıştıracağın CPU/GPU sunucusunun barındırma maliyeti olabilir.
