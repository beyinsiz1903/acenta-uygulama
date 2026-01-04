# Syroce Match Alerts Webhook — Signature Verification (v1/v2)

Bu doküman, Syroce “match alert” webhook’larını alan sistemlerin **isteğin Syroce’tan geldiğini doğrulaması** için gereken imza (HMAC) mekanizmasını anlatır.

## 1) Gönderilen Event’ler

Syroce iki tip event gönderebilir:

* **Single item:** `match.alert`
* **Batch:** `match.alert.batch`
* (Test) `match.alert.test`

Header:

* `X-Syroce-Event: match.alert | match.alert.batch | match.alert.test`
* `X-Syroce-Org: <organization_id>`
* `X-Syroce-Signature: sha256=<hex>` *(yalnızca policy’de webhook_secret set ise)*

## 2) Signature nasıl üretiliyor?

Eğer `webhook_secret` tanımlıysa Syroce şu imzayı üretir:

* **Algoritma:** HMAC-SHA256
* **Input:** HTTP request body’nin **raw bytes** hali (JSON string’in birebir gönderilen hali)
* **Secret:** policy’deki `webhook_secret`
* **Header format:**
  `X-Syroce-Signature: sha256=<hmac_hex>`

Pseudo:

```
sig = HMAC_SHA256(secret, raw_body_bytes)
header = "sha256=" + hex(sig)
```

> Önemli: Doğrulamada **raw body** kullanılmalı. JSON parse edip tekrar stringify etmek imzayı bozabilir (whitespace/key order).

## 3) Doğrulama kuralları

Webhook endpoint’inizde:

1. Raw body’yi alın (bytes/string)
2. `X-Syroce-Signature` header’ını okuyun
3. `sha256=` prefix’ini ayırın
4. Aynı HMAC’i hesaplayın
5. `constant-time compare` ile karşılaştırın
6. Uyuşmuyorsa `401 Unauthorized` dönün

Ek öneriler:

* `X-Syroce-Org` ile beklenen org’ı kontrol edin
* `Content-Type: application/json` bekleyin
* İsterseniz IP allowlist / rate limit ekleyin (opsiyonel)

---

# Node.js (Express) Örnek

> Express’te **rawBody** almak için `express.json({ verify })` kullanın.

```js
import express from "express";
import crypto from "crypto";

const app = express();

// 1) raw body capture
app.use(
  express.json({
    verify: (req, res, buf) => {
      req.rawBody = buf; // Buffer
    },
  })
);

function verifySyroceSignature(req, secret) {
  const sigHeader = req.header("X-Syroce-Signature") || "";
  if (!sigHeader.startsWith("sha256=")) return false;

  const expected = sigHeader.slice("sha256=".length);
  const computed = crypto
    .createHmac("sha256", secret)
    .update(req.rawBody) // raw bytes
    .digest("hex");

  // constant-time compare
  const a = Buffer.from(expected, "hex");
  const b = Buffer.from(computed, "hex");
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

app.post("/webhook/match-alerts", (req, res) => {
  const secret = process.env.SYROCE_WEBHOOK_SECRET || "";

  // secret set değilse: signature beklemeyebilirsiniz (policy’ye bağlı)
  if (secret) {
    const ok = verifySyroceSignature(req, secret);
    if (!ok) return res.status(401).json({ ok: false, error: "INVALID_SIGNATURE" });
  }

  const event = req.header("X-Syroce-Event");
  const org = req.header("X-Syroce-Org");
  const payload = req.body;

  // TODO: handle events
  return res.json({ ok: true, received: true, event, org });
});

app.listen(3000, () => console.log("listening on :3000"));
```

---

# Python (FastAPI) Örnek

FastAPI’de raw body’yi `await request.body()` ile alın.

```py
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

def verify_sig(raw_body: bytes, secret: str, sig_header: str) -> bool:
  if not sig_header or not sig_header.startswith("sha256="):
      return False
  expected = sig_header[len("sha256="):]

  computed = hmac.new(
      key=secret.encode("utf-8"),
      msg=raw_body,
      digestmod=hashlib.sha256
  ).hexdigest()

  # constant-time compare
  return hmac.compare_digest(expected, computed)

@app.post("/webhook/match-alerts")
async def match_alerts_webhook(request: Request):
  # pratikte secret'i header'dan değil env'den okuyun:
  # secret = os.environ["SYROCE_WEBHOOK_SECRET"]
  secret = (request.headers.get("x-syroce-webhook-secret") or "").strip()

  raw = await request.body()
  sig = request.headers.get("x-syroce-signature", "")

  if secret:
      if not verify_sig(raw, secret, sig):
          raise HTTPException(status_code=401, detail="INVALID_SIGNATURE")

  event = request.headers.get("x-syroce-event")
  org = request.headers.get("x-syroce-org")

  payload = await request.json()
  return {"ok": True, "received": True, "event": event, "org": org}
```

> Not: Örnekte secret header’dan alınıyor gibi gösteriliyor ama gerçek kullanımda **env/config**’ten alın.

---

# Test için önerilen doğrulama

1. Policy’de `webhook_secret` set et
2. “Test Webhook” butonuna bas
3. Endpoint log’unda:

   * `X-Syroce-Event: match.alert.test`
   * signature doğrulaması true

4. Yanlış secret ile doğrulama: 401 dönmeli

---

## “Ben signature istemiyorum” durumu

Policy’de `webhook_secret = null` ise Syroce **signature header göndermeyebilir**.
Güvenlik isteniyorsa secret set edilmesi önerilir.

---

## Sonraki iyileştirme (opsiyonel, v3)

* Header’a `X-Syroce-Timestamp` ekleyip replay protection (örn. 5 dk penceresi)
* `X-Syroce-Id` ile idempotency / duplicate detection
