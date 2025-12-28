"""
Kwork AI PM - Kwork Service
Kwork birjasi bilan ishlash uchun servis
"""
import httpx
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from models.settings import Settings


class KworkService:
    """Kwork API bilan ishlash uchun servis"""
    
    BASE_URL = "https://kwork.ru"
    LOGIN_URL = f"{BASE_URL}/api/user/login"
    PROJECTS_URL = f"{BASE_URL}/projects"
    
    DEFAULT_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://kwork.ru",
        "Referer": "https://kwork.ru/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cookies: Dict[str, str] = {}
        self._user_id: Optional[str] = None
        self._is_logged_in: bool = False
    
    async def load_session(self) -> bool:
        """Ma'lumotlar bazasidan sessiyani yuklash"""
        try:
            # Cookies olish
            result = await self.db.execute(
                select(Settings).where(Settings.key == "kwork_cookies")
            )
            cookies_setting = result.scalar_one_or_none()
            
            if cookies_setting and cookies_setting.value:
                self._cookies = json.loads(cookies_setting.value)
            
            # User ID olish
            result = await self.db.execute(
                select(Settings).where(Settings.key == "kwork_user_id")
            )
            user_id_setting = result.scalar_one_or_none()
            
            if user_id_setting and user_id_setting.value:
                self._user_id = user_id_setting.value
            
            # Login holati
            result = await self.db.execute(
                select(Settings).where(Settings.key == "kwork_logged_in")
            )
            logged_in_setting = result.scalar_one_or_none()
            
            self._is_logged_in = logged_in_setting and logged_in_setting.value == "true"
            
            return self._is_logged_in
        except Exception as e:
            print(f"Session yuklashda xato: {e}")
            return False
    
    async def _save_setting(self, key: str, value: str, category: str = "kwork"):
        """Sozlamani saqlash"""
        result = await self.db.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(
                key=key,
                value=value,
                category=category,
                is_secret=(key == "kwork_cookies")
            )
            self.db.add(setting)
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Kwork ga kirish"""
        payload = {
            "l_username": username,
            "l_password": password,
            "jlog": 1,
            "recaptcha_pass_token": "",
            "track_client_id": False,
            "smart-token": "",
            "l_remember_me": "1"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.LOGIN_URL,
                    json=payload,
                    headers=self.DEFAULT_HEADERS
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP xato: {response.status_code}"
                    }
                
                data = response.json()
                
                # Response tekshirish
                if data.get("success") == False or data.get("error"):
                    return {
                        "success": False,
                        "error": data.get("error", "Login muvaffaqiyatsiz")
                    }
                
                # Cookies olish
                cookies = {}
                for cookie in response.cookies.jar:
                    cookies[cookie.name] = cookie.value
                
                # User ID olish
                user_id = None
                if "userId" in cookies:
                    user_id = cookies["userId"]
                
                # Bazaga saqlash
                self._cookies = cookies
                self._user_id = user_id
                self._is_logged_in = True
                
                await self._save_setting("kwork_cookies", json.dumps(cookies))
                await self._save_setting("kwork_user_id", user_id or "")
                await self._save_setting("kwork_logged_in", "true")
                await self._save_setting("kwork_username", username)
                await self.db.commit()
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "message": "Muvaffaqiyatli kirdingiz"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Xatolik: {str(e)}"
            }
    
    async def logout(self) -> Dict[str, Any]:
        """Chiqish va sessiyani tozalash"""
        try:
            self._cookies = {}
            self._user_id = None
            self._is_logged_in = False
            
            await self._save_setting("kwork_cookies", "")
            await self._save_setting("kwork_user_id", "")
            await self._save_setting("kwork_logged_in", "false")
            await self.db.commit()
            
            return {
                "success": True,
                "message": "Muvaffaqiyatli chiqdingiz"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Xatolik: {str(e)}"
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Joriy holat"""
        await self.load_session()
        
        # Username olish
        result = await self.db.execute(
            select(Settings).where(Settings.key == "kwork_username")
        )
        username_setting = result.scalar_one_or_none()
        
        # Oxirgi tekshiruv vaqti
        result = await self.db.execute(
            select(Settings).where(Settings.key == "kwork_last_check")
        )
        last_check_setting = result.scalar_one_or_none()
        
        return {
            "logged_in": self._is_logged_in,
            "user_id": self._user_id,
            "username": username_setting.value if username_setting else None,
            "last_check": last_check_setting.value if last_check_setting else None
        }
    
    async def fetch_projects(self) -> Dict[str, Any]:
        """Birjadan e'lonlarni olish"""
        await self.load_session()
        
        if not self._is_logged_in or not self._cookies:
            return {
                "success": False,
                "error": "Avval login qiling"
            }
        
        try:
            # Cookie string yaratish
            cookie_str = "; ".join([f"{k}={v}" for k, v in self._cookies.items()])
            
            headers = {
                **self.DEFAULT_HEADERS,
                "Cookie": cookie_str,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(
                    self.PROJECTS_URL,
                    headers=headers
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP xato: {response.status_code}"
                    }
                
                # HTML dan JSON ni olish
                html = response.text
                import re
                
                # wantsListData ichidan wants ni topish
                # 1-usul: "wants": [{...}] - asosiy ro'yxat
                wants = []
                
                # wantsListData strukturasini topish uchun
                # pagination.data yoki wants massivini izlaymiz
                match = re.search(r'"wantsListData"\s*:\s*\{', html)
                
                if match:
                    start_pos = match.start()
                    # wantsListData ob'ektining oxirini topish
                    # JSON ni bracket counting bilan ajratamiz
                    
                    # Sodda usul - "wants": [ ni topib, undagi ob'ektlarni olish
                    # pagination.data dan olish
                    pagination_match = re.search(
                        r'"pagination"\s*:\s*\{\s*"current_page"[^}]*"data"\s*:\s*\[',
                        html
                    )
                    
                    if pagination_match:
                        # data massivining boshlanish pozitsiyasi
                        data_start = pagination_match.end() - 1  # [ dan oldin
                        
                        # Bracket counting bilan massiv oxirini topish
                        bracket_count = 0
                        data_end = data_start
                        
                        for i, char in enumerate(html[data_start:data_start + 500000]):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    data_end = data_start + i + 1
                                    break
                        
                        if data_end > data_start:
                            try:
                                data_json = html[data_start:data_end]
                                wants = json.loads(data_json)
                            except json.JSONDecodeError:
                                pass
                    
                    # Agar pagination.data topilmasa, "wants": [ ni qidirish
                    if not wants:
                        wants_match = re.search(r'"wants"\s*:\s*\[', html[start_pos:start_pos + 600000])
                        if wants_match:
                            wants_start = start_pos + wants_match.end() - 1
                            
                            bracket_count = 0
                            wants_end = wants_start
                            
                            for i, char in enumerate(html[wants_start:wants_start + 500000]):
                                if char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                                    if bracket_count == 0:
                                        wants_end = wants_start + i + 1
                                        break
                            
                            if wants_end > wants_start:
                                try:
                                    wants_json = html[wants_start:wants_end]
                                    wants = json.loads(wants_json)
                                except json.JSONDecodeError:
                                    pass
                
                if not wants:
                    return {
                        "success": False,
                        "error": "wantsListData topilmadi yoki bo'sh"
                    }
                
                # Oxirgi tekshiruv vaqtini yangilash
                await self._save_setting(
                    "kwork_last_check", 
                    datetime.utcnow().isoformat()
                )
                await self.db.commit()
                
                return {
                    "success": True,
                    "wants": wants,
                    "count": len(wants)
                }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Xatolik: {str(e)}"
            }
    
    def parse_project(self, want: Dict) -> Dict[str, Any]:
        """E'lon ma'lumotlarini parse qilish - barcha ma'lumotlarni olish"""
        user = want.get("user", {})
        user_data = user.get("data", {})
        
        # Sanalarni parse qilish
        date_expire = None
        date_active = None
        date_create = None
        
        if want.get("date_expire"):
            try:
                from datetime import datetime
                date_expire = datetime.strptime(want["date_expire"], "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        if want.get("date_active"):
            try:
                from datetime import datetime
                date_active = datetime.strptime(want["date_active"], "%Y-%m-%d %H:%M:%S")
            except:
                pass
                
        if want.get("date_create"):
            try:
                from datetime import datetime
                date_create = datetime.strptime(want["date_create"], "%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        return {
            # Asosiy
            "kwork_id": str(want.get("id", "")),
            "title": want.get("name", ""),
            "description": want.get("description", ""),
            "budget": want.get("priceLimit", ""),
            "category": want.get("categoryName", ""),
            "category_id": want.get("category_id", ""),
            
            # To'liq JSON
            "kwork_json": json.dumps(want, ensure_ascii=False),
            
            # Buyurtmachi
            "client_id": str(user.get("USERID", "")),
            "client_name": user.get("username", ""),
            "client_avatar": user.get("profilepicture", ""),
            "client_profile_url": want.get("wantUserGetProfileUrl", ""),
            "client_wants_count": int(user_data.get("wants_count", 0)) if user_data.get("wants_count") else None,
            "client_hired_percent": int(user_data.get("wants_hired_percent", 0)) if user_data.get("wants_hired_percent") else None,
            
            # E'lon detallari
            "max_days": int(want.get("max_days", 0)) if want.get("max_days") else None,
            "price_limit": want.get("priceLimit", ""),
            "views_count": int(want.get("views_dirty", 0)) if want.get("views_dirty") else None,
            "kwork_status": want.get("status", ""),
            "time_left": want.get("timeLeft", ""),
            
            # Sanalar
            "date_expire": date_expire,
            "date_active": date_active,
            "date_create_kwork": date_create,
            
            # URL
            "url": f"https://kwork.ru/projects/{want.get('id', '')}"
        }
