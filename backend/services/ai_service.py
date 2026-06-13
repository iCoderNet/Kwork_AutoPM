"""
Kwork AI PM - AI Service
Gemini, OpenAI, and Anthropic API integration
"""
import httpx
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.settings import Settings


class AIService:
    """AI Service for generating responses using various LLM providers"""
    
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    OPENAI_BASE_URL = "https://api.openai.com/v1/chat/completions"
    ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str, system_prompt: str = "", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.base_url = base_url  # Custom OpenAI-compatible endpoint

    @classmethod
    async def from_db(cls, db: AsyncSession) -> Optional["AIService"]:
        """Create AIService from database settings"""
        result = await db.execute(select(Settings).where(Settings.key == "ai_api_key"))
        api_key_setting = result.scalar_one_or_none()

        result = await db.execute(select(Settings).where(Settings.key == "ai_model"))
        model_setting = result.scalar_one_or_none()

        result = await db.execute(select(Settings).where(Settings.key == "ai_prompt"))
        prompt_setting = result.scalar_one_or_none()

        result = await db.execute(select(Settings).where(Settings.key == "ai_base_url"))
        base_url_setting = result.scalar_one_or_none()

        if not api_key_setting or not api_key_setting.value:
            return None

        model = model_setting.value if model_setting else "gemini-2.0-flash"
        prompt = prompt_setting.value if prompt_setting else ""
        base_url = base_url_setting.value if base_url_setting else ""

        return cls(
            api_key=api_key_setting.value,
            model=model,
            system_prompt=prompt,
            base_url=base_url,
        )

    def is_custom(self) -> bool:
        """Custom OpenAI-compatible endpoint (base_url to'ldirilgan)"""
        return bool(self.base_url)

    def is_gemini(self) -> bool:
        return self.model.startswith("gemini")

    def is_openai(self) -> bool:
        return self.model.startswith("gpt")

    def is_anthropic(self) -> bool:
        return self.model.startswith("claude")
    
    async def generate_response(self, job_description: str, budget: str) -> Dict[str, Any]:
        """Generate AI response for a job description"""
        
        # Build the prompt
        full_prompt = self._build_prompt(job_description, budget)
        
        try:
            if self.is_custom():
                return await self._call_custom(full_prompt)
            elif self.is_gemini():
                return await self._call_gemini(full_prompt)
            elif self.is_openai():
                return await self._call_openai(full_prompt)
            elif self.is_anthropic():
                return await self._call_anthropic(full_prompt)
            else:
                return {
                    "success": False,
                    "error": f"Noma'lum model: {self.model}. base_url kiriting yoki modelni to'g'ri yozing."
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_prompt(self, job_description: str, budget: str) -> str:
        """Build full prompt with system prompt and job description"""
        
        default_prompt = """Sen senior-level freelancer va professional AI assistant sifatida ishlaysan.
Sening vazifang — Kwork birjasidagi loyiha tavsifini tahlil qilish va avtomatik, halol va real otklik (proposal) tayyorlash.

SEN:
- marketingchi EMASSAN
- yolg‘on va’da BERMAYSAN
- faqat real va bajariladigan ishlarni tanlaysan
- biznes va risk nuqtai nazaridan qaror qilasan

⚠️ QAT’IY QOIDALAR:
- Faqat belgilangan JSON formatda javob qaytar
- Hech qanday izoh, markdown yoki tashqi matn yozma
- Agar risk yuqori bo‘lsa — proposal YOZILMAYDI
- Yolg‘on va’dalar, kafolatlar, bo‘rttirishlar TAQIQLANADI

========================
📌 HTML BILAN ISHLASH
========================
- Kelayotgan loyiha matni HTML bo‘lishi mumkin
- Barcha HTML taglarni olib tashla
- Tahlil faqat toza matn asosida qilinsin
- original HTML alohida saqlansin

========================
📌 BIZNING PROFIL
========================
Ko‘nikmalar:
- PHP (Laravel)
- REST API
- MySQL
- React (basic–middle)
- HTML / CSS
- JavaScript
- Performance optimization
- Bug fixing
- Existing loyihalarni qo‘llab-quvvatlash

QILMAYMIZ:
- Gambling / betting
- Adult (18+)
- Crypto scam / piramida
- Juda katta (enterprise) loyihalar
- Real bo‘lmagan byudjet va muddatlar

Daraja: Middle+
Ish tili: Ruscha (professional, qisqa)

========================
💰 NARXLASH QOIDALARI
========================
- 1–3 soat: 10–20 USD
- 1–3 kun: 30–80 USD
- 1+ hafta: 100+ USD

Valyuta:
- Ichki hisob: USD
- Konvertatsiya: 1 USD = 90 RUB
- JSON’da faqat RUB qaytar

========================
⏱ MUDDAT QOIDALARI
========================
- Muddat har doim taxminiy (range)
- Kichik ish: soatlarda (2–4 soat)
- O‘rtacha ish: kunlarda (1–3 kun)
- Katta ish: kun / hafta (3–7 kun, 1–2 hafta)
- Juda optimistik muddatlar TAQIQLANADI

========================
🧠 "KAM YOZ, LEKIN ANIQLI SOT" REJIMI
========================
Otklik 3–5 jumladan oshmasin.

Struktura:
1. Muammo mohiyatini qayta ayt
2. Shu turdagi ish bilan tanish ekaningni ko‘rsat
3. Xavfni kamaytir (avval ko‘raman, aniqlayman)
4. Oxiri — yumshoq savol

TAQIQLANADI:
- “гарантирую”
- “лучший”
- “без проблем”
- “за 1 час”
- “любой сложности”

========================
📊 CONFIDENCE SCORE
========================
0.0 – 1.0 oralig‘ida bahola.

Asoslar:
- Skill mosligi
- Loyiha murakkabligi
- Byudjet realistikligi
- Umumiy aniqlik

========================
⚠️ ADVANCED RISK MODEL
========================
Quyidagi risk komponentlarini bahola (0.0 – 1.0):

1. skill_risk
2. confidence_risk = 1 - confidence_score
3. price_risk
4. time_risk
5. communication_risk

Umumiy risk hisoblash:
total_risk =
  skill_risk * 0.30
+ confidence_risk * 0.25
+ price_risk * 0.20
+ time_risk * 0.15
+ communication_risk * 0.10

QAROR:
- Agar total_risk > 0.65 → can_take = false
- Bunday holatda proposal_text BO‘SH bo‘lsin
- Majburiy doim bo'lishi kerak  [can_take, confidence_score, risk_score, reason, estimated_price_rub, estimated_time_human, estimated_time_seconds]

========================
📤 CHIQISH (QAT’IY JSON)
========================
{
  "can_take": true | false,
  "confidence_score": number,
  "risk_score": number,

  "reason": {
    "ru": "string",
    "uz": "string"
  },

  "estimated_price_rub": number,

  "estimated_time_human": string,
  "estimated_time_seconds": number,

  "proposal_text": {
    "ru": "string",
    "uz": "string"
  },

  "full_task_text": {
    "ru": "HTML’dan tozalangan matn",
    "uz": "HTML’dan tozalangan matn faqat uzbekcha tarjimada"
  }
}"""
        
        system = self.system_prompt if self.system_prompt else default_prompt
        
        return f"""{system}

========================
📥 KIRISH MA’LUMOTI
========================
Quyida Kwork’dagi loyiha tavsifi beriladi:

{job_description}
Mijozning tahminiy budgeti: {budget}

Javob:"""
    
    async def _call_custom(self, prompt: str) -> Dict[str, Any]:
        """OpenAI-compatible custom endpoint (masalan gpt-oss-120b)"""
        # base_url oxirida /chat/completions bo'lmasa qo'shamiz
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                try:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    error_msg = response.text
                return {
                    "success": False,
                    "error": f"Custom API xatosi ({response.status_code}): {error_msg}",
                }

            data = response.json()
            try:
                text = data["choices"][0]["message"]["content"]
                return {"success": True, "text": text, "model": self.model, "raw_response": data}
            except (KeyError, IndexError) as e:
                return {"success": False, "error": f"Javobni o'qishda xato: {e}"}

    async def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Google Gemini API"""
        url = f"{self.GEMINI_BASE_URL}/{self.model}:generateContent"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                return {
                    "success": False,
                    "error": f"Gemini API xatosi ({response.status_code}): {error_msg}"
                }
            
            data = response.json()
            
            # Extract text from Gemini response
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {
                    "success": True,
                    "text": text,
                    "model": self.model,
                    "raw_response": data
                }
            except (KeyError, IndexError) as e:
                return {
                    "success": False,
                    "error": f"Javobni o'qishda xato: {str(e)}",
                    "raw_response": data
                }
    
    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.OPENAI_BASE_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                return {
                    "success": False,
                    "error": f"OpenAI API xatosi ({response.status_code}): {error_msg}"
                }
            
            data = response.json()
            
            try:
                text = data["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "text": text,
                    "model": self.model,
                    "raw_response": data
                }
            except (KeyError, IndexError) as e:
                return {
                    "success": False,
                    "error": f"Javobni o'qishda xato: {str(e)}"
                }
    
    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.ANTHROPIC_BASE_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                return {
                    "success": False,
                    "error": f"Anthropic API xatosi ({response.status_code}): {error_msg}"
                }
            
            data = response.json()
            
            try:
                text = data["content"][0]["text"]
                return {
                    "success": True,
                    "text": text,
                    "model": self.model,
                    "raw_response": data
                }
            except (KeyError, IndexError) as e:
                return {
                    "success": False,
                    "error": f"Javobni o'qishda xato: {str(e)}"
                }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test AI API connection with a simple request"""
        test_prompt = "Salom, sen kim? Bir so'z bilan javob ber."
        return await self.generate_response(test_prompt, "")
