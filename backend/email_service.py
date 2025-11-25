"""
Email Service - Mock Implementation
Gerçek e-posta göndermek için SendGrid veya SMTP entegrasyonu eklenebilir
"""
import random
from datetime import datetime

class EmailService:
    """Mock email service - console'a yazdırır"""
    
    def __init__(self):
        self.mode = "mock"  # "mock" veya "production"
    
    def generate_verification_code(self) -> str:
        """6 haneli onay kodu oluştur"""
        return str(random.randint(100000, 999999))
    
    def generate_reset_token(self) -> str:
        """Şifre sıfırlama token'ı oluştur"""
        import secrets
        return secrets.token_urlsafe(32)
    
    async def send_verification_code(self, email: str, code: str, name: str = None) -> bool:
        """E-posta doğrulama kodu gönder"""
        try:
            print("\n" + "="*60)
            print("📧 E-POSTA DOĞRULAMA KODU")
            print("="*60)
            print(f"Alıcı: {email}")
            if name:
                print(f"İsim: {name}")
            print(f"Kod: {code}")
            print(f"Geçerlilik: 15 dakika")
            print(f"Gönderim Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60 + "\n")
            
            # Gerçek e-posta gönderimi için:
            # if self.mode == "production":
            #     # SendGrid, SMTP, vb. entegrasyonu
            #     pass
            
            return True
        except Exception as e:
            print(f"❌ E-posta gönderim hatası: {e}")
            return False
    
    async def send_password_reset_code(self, email: str, code: str, name: str = None) -> bool:
        """Şifre sıfırlama kodu gönder"""
        try:
            print("\n" + "="*60)
            print("🔐 ŞİFRE SIFIRLAMA KODU")
            print("="*60)
            print(f"Alıcı: {email}")
            if name:
                print(f"İsim: {name}")
            print(f"Kod: {code}")
            print(f"Geçerlilik: 15 dakika")
            print(f"Gönderim Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60 + "\n")
            
            return True
        except Exception as e:
            print(f"❌ E-posta gönderim hatası: {e}")
            return False
    
    async def send_welcome_email(self, email: str, name: str) -> bool:
        """Hoşgeldin e-postası gönder"""
        try:
            print("\n" + "="*60)
            print("🎉 HOŞGELDİN E-POSTASI")
            print("="*60)
            print(f"Alıcı: {email}")
            print(f"İsim: {name}")
            print(f"Mesaj: Hesabınız başarıyla oluşturuldu!")
            print(f"Gönderim Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60 + "\n")
            
            return True
        except Exception as e:
            print(f"❌ E-posta gönderim hatası: {e}")
            return False

# Global email service instance
email_service = EmailService()
