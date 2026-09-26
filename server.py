import os, re, tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from paddleocr import PaddleOCR

app = Flask(__name__)
CORS(app)

# High-accuracy server models. First run downloads model weights.
ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_server_det",
    text_recognition_model_name="PP-OCRv5_server_rec",
    use_doc_orientation_classify=True,
    use_doc_unwarping=True,
    use_textline_orientation=True,
)

def money(s):
    if not s: return None
    s=re.sub(r"[^\d,.\-]","",s)
    if "," in s: s=s.replace(".","").replace(",",".")
    try: return round(float(s),2)
    except: return None

def parse_receipt(lines):
    text="\n".join(x["text"] for x in lines)
    up=text.upper()
    merchant=None
    known=["MAYÇO","MAYCO","MİGROS","MIGROS","BİM","BIM","A101","ŞOK","SOK","CARREFOUR","METRO","MACROCENTER","FİLE MARKET","FILE MARKET"]
    for k in known:
        if k in up:
            merchant="MAYÇO" if k in ("MAYÇO","MAYCO") else k
            break
    if not merchant:
        bad=re.compile(r"FİŞ|FIS|TARİH|TARIH|SAAT|VERGİ|VERGI|KDV|TOP|POS|BANKA|V\.?D",re.I)
        cand=[x["text"] for x in lines[:15] if len(x["text"])<55 and re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]{3}",x["text"]) and not bad.search(x["text"])]
        merchant=cand[0] if cand else None

    dm=re.search(r"\b([0-3]?\d[./-][01]?\d[./-](?:20)?\d{2,4})\b",text)
    tm=re.search(r"\b([0-2]?\d[:.][0-5]\d)\b",text)
    rm=re.search(r"(?:FİŞ|FIS|FİS|BELGE)\s*(?:NO|N0|NUMARASI)?\s*[:#]?\s*\*?\s*([0-9]{2,12})",text,re.I)

    vat=None
    for i,x in enumerate(lines):
        if re.search(r"\bKDV\b",x["text"],re.I):
            neighborhood=" ".join(y["text"] for y in lines[i:i+3])
            m=re.search(r"(\d{1,7}[,.]\d{2})",neighborhood)
            if m: vat=money(m.group(1)); break

    total=None
    # Prefer TOP/TOPLAM lines, then repeated transaction amount.
    for i,x in enumerate(lines):
        if re.search(r"\b(TOP|TOPLAM|GENEL TOPLAM|ÖDENECEK|ODENECEK)\b",x["text"],re.I):
            neighborhood=" ".join(y["text"] for y in lines[i:i+3])
            vals=re.findall(r"(\d{1,7}[,.]\d{2})",neighborhood)
            if vals:
                total=money(vals[-1]); break

    payment="Kart" if re.search(r"EFT.?POS|KREDİ|KREDI|TROY|VISA|MASTERCARD|BANKA KART",up) else ("Nakit" if "NAKİT" in up or "NAKIT" in up else None)
    return {"merchant":merchant,"date":dm.group(1) if dm else None,"time":tm.group(1).replace(".",":") if tm else None,
            "receipt_no":rm.group(1) if rm else None,"vat":vat,"total":total,"payment":payment}

def flatten_result(result):
    out=[]
    # PaddleOCR 3.x Result objects can expose a json/res payload; handle common shapes defensively.
    for page in result:
        data=getattr(page,"json",None)
        if callable(data): data=data()
        if isinstance(data,str):
            import json as _json
            try:data=_json.loads(data)
            except:data=None
        if not isinstance(data,dict):
            data=getattr(page,"res",None)
        if isinstance(data,dict) and "res" in data and isinstance(data["res"],dict): data=data["res"]
        if isinstance(data,dict):
            texts=data.get("rec_texts") or []
            scores=data.get("rec_scores") or []
            for i,t in enumerate(texts):
                if str(t).strip():
                    out.append({"text":str(t).strip(),"score":float(scores[i]) if i<len(scores) else 0.0})
    return out

@app.get("/health")
def health(): return {"ok":True}

@app.post("/ocr")
def do_ocr():
    f=request.files.get("image")
    if not f: return jsonify(error="image alanı gerekli"),400
    suffix=os.path.splitext(f.filename or ".jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix,delete=False) as tmp:
        f.save(tmp.name); path=tmp.name
    try:
        result=ocr.predict(path)
        lines=flatten_result(result)
        if not lines: return jsonify(error="Metin algılanamadı"),422
        text="\n".join(x["text"] for x in lines)
        return jsonify(lines=lines,text=text,receipt=parse_receipt(lines))
    finally:
        try: os.remove(path)
        except: pass

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","8080")))
