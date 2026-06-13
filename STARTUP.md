# Kwork AUTO-PM — Yo'riqnoma

## Sayt nima qiladi?

Kwork.ru birjasini **avtomatik skanerlaydi**. Har bir yangi loyiha uchun:
1. AI tahlil qiladi (can_take?, risk, narx, taklif matni)
2. Qabul qilish mumkin bo'lsa — Telegram guruhga xabar yuboradi
3. Dashboard da barcha loyihalar va statistika ko'rinadi

---

## O'rnatish

```bash
cd Kwork-AUTO-PM/backend
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Eski venv bo'lsa** (passlib xatosi):
> ```bash
> pip uninstall passlib -y
> pip install -r requirements.txt
> ```

---

## Ishga tushirish

```bash
cd Kwork-AUTO-PM/backend
source venv/bin/activate
python main.py
```

Muvaffaqiyatli ishga tushganda:
```
🚀 Starting Kwork AI PM...
✅ Database initialized
✅ Default settings and admin user ready
⏰ Scheduler ishga tushdi — har 60 sekundda skanerlaydi
🌐 Server running at https://...
```

---

## Manzillar

| URL | Nima |
|-----|------|
| `http://localhost:8000/` | Login |
| `http://localhost:8000/dashboard` | Dashboard |
| `http://localhost:8000/docs` | Swagger API |
| `http://localhost:8000/health` | Health check |

**Default login:** `admin` / `admin123`

---

## Admin panel sozlamalari

Dashboard → ⚙️ Settings bo'limiga kiring.

### 1. Kwork

| Maydon | Nima kiriting |
|--------|---------------|
| Kwork login | Kwork.ru username |
| Kwork parol | Kwork.ru parol |

Saqlangandan keyin **"Kwork ga kirish"** tugmasini bosing.

---

### 2. AI sozlamalari

| Maydon | Misol |
|--------|-------|
| AI yoqilgan | `true` / `false` |
| AI model | (quyida) |
| AI API kaliti | API key |
| Custom base URL | (quyida) |
| AI prompt | bo'sh → default prompt ishlatiladi |

#### Qaysi model ishlatish?

| Model | API kaliti | Base URL |
|-------|-----------|----------|
| `gemini-2.0-flash` | Google AI Studio | bo'sh |
| `gpt-4` / `gpt-4o` | OpenAI | bo'sh |
| `claude-3-5-sonnet-20241022` | Anthropic | bo'sh |
| `openai/gpt-oss-120b` | `sk-_RFXXpNRwyAc5ap6XUztNQ` | `https://p950-w009-runai-p950.runai-inference.dc.uz/v1` |

**O'zimizning AI (gpt-oss-120b) uchun:**
```
AI model:    openai/gpt-oss-120b
AI API key:  sk-_RFXXpNRwyAc5ap6XUztNQ
Base URL:    https://p950-w009-runai-p950.runai-inference.dc.uz/v1
```

#### Sozlamalarni tekshirish
Settings sahifasida **"AI ni test qilish"** tugmasi mavjud — shu orqali ulanganligi tekshiriladi.

---

### 3. Telegram

| Maydon | Nima |
|--------|------|
| Bot token | `@BotFather` dan olingan token |
| Group ID | `-100xxxxxxxxx` formatida |
| Telegram yoqilgan | `true` |

Saqlangandan keyin:
1. **"Telegram test"** — bot ulanganligi va guruhga kirishi tekshiriladi
2. **"Webhook o'rnatish"** — Telegram callback tugmalari uchun (server ochiq bo'lishi kerak)

---

### 4. Tizim

| Maydon | Default | Nima |
|--------|---------|------|
| Skanerlash intervali | `60` | Necha sekundda bir Kwork skanerlanadi |
| Avtomatik javob | `false` | `true` bo'lsa AI tahlil + Telegram avtomatik ishlaydi |

> **Diqqat:** `Avtomatik javob = false` bo'lsa, loyihalar DB ga saqlanadi, lekin AI ishlamaydi.  
> `true` qiling — u holda to'liq pipeline ishlaydi.

---

## Cron (avtomatik skanerlash)

Server ishga tushganda **APScheduler** avtomatik boshlanadi.  
`Skanerlash intervali` settings da o'zgartirilganda server qayta ishga tushirilishi kerak.

Qo'lda tekshirish: `POST /api/kwork/check-projects`

---

## Muammolar

| Xato | Yechim |
|------|--------|
| `bcrypt` xatosi | `pip uninstall passlib -y && pip install -r requirements.txt` |
| Port band | `lsof -ti:8000 \| xargs kill -9` |
| DB reset | `rm backend/data/kwork_pm.db` va serverni qayta ishga tushirish |
| AI ishlamayapti | Settings → "AI test" tugmasini bosing, xatoni ko'ring |
