# 🔒 Security Hardening Guide - Hotel PMS

## Overview
Comprehensive security hardening guide for production deployment of Hotel PMS system.

---

## 🛡️ Application Security

### 1. JWT Token Security

**Current Implementation:** ✅
- Tokens expire after 7 days
- HS256 algorithm
- Secret key from environment

**Enhancements:**
```python
# backend/auth.py
import secrets

# Generate strong secret key
JWT_SECRET = os.environ.get('JWT_SECRET') or secrets.token_urlsafe(32)

# Token configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24  # Shorter expiration
JWT_REFRESH_EXPIRATION_DAYS = 7

# Add token blacklist for logout
token_blacklist = set()

def blacklist_token(token: str):
    """Add token to blacklist"""
    token_blacklist.add(token)
    # Also store in Redis with expiration
    cache.set(f"blacklist:{token}", True, ttl=86400)

def is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    return token in token_blacklist or cache.get(f"blacklist:{token}")
```

### 2. Password Security

**Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

**Implementation:**
```python
import re
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password"""
    return pwd_context.verify(plain_password, hashed_password)
```

### 3. Input Validation & Sanitization

**SQL/NoSQL Injection Prevention:**
```python
from pydantic import BaseModel, validator, Field
import bleach

class BookingCreate(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    phone: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    
    @validator('guest_name')
    def sanitize_name(cls, v):
        """Sanitize HTML from name"""
        return bleach.clean(v, strip=True)
    
    @validator('email')
    def normalize_email(cls, v):
        """Normalize email"""
        return v.lower().strip()
```

### 4. XSS Protection

**Frontend:**
```javascript
// frontend/src/utils/security.js
export const sanitizeHTML = (dirty) => {
  const div = document.createElement('div');
  div.textContent = dirty;
  return div.innerHTML;
};

export const escapeHTML = (unsafe) => {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

// Use in components
const DisplayName = ({ name }) => {
  return <div>{escapeHTML(name)}</div>;
};
```

### 5. CSRF Protection

**Implementation:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get('CORS_ORIGINS', '').split(','),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    expose_headers=["X-CSRF-Token"]
)

# CSRF token generation
import secrets

def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_urlsafe(32)

# Store in session and verify
@app.post("/api/protected-action")
async def protected_action(
    csrf_token: str = Header(...),
    session_token: str = Depends(get_session_token)
):
    if csrf_token != session_token:
        raise HTTPException(status_code=403, detail="CSRF token mismatch")
    # Process action
```

---

## 🗄️ Database Security

### 1. MongoDB Authentication
```javascript
// Enable authentication
use admin
db.createUser({
  user: "admin",
  pwd: "strong_password_here",
  roles: ["root"]
})

// Create application user
use hotel_pms
db.createUser({
  user: "app_user",
  pwd: "strong_app_password",
  roles: [
    {role: "readWrite", db: "hotel_pms"},
    {role: "dbAdmin", db: "hotel_pms"}
  ]
})
```

### 2. Connection String Security
```python
# NEVER commit connection strings
# Use environment variables

MONGO_URL = os.environ.get('MONGO_URL')
# mongodb://user:password@host:port/database?authSource=admin&tls=true
```

### 3. Encryption at Rest
```yaml
# mongod.conf
security:
  enableEncryption: true
  encryptionKeyFile: /path/to/keyfile
```

### 4. Field-Level Encryption
```python
from pymongo.encryption import ClientEncryption

# Encrypt sensitive fields
async def encrypt_sensitive_data(data: dict) -> dict:
    """Encrypt PII data"""
    encrypted = data.copy()
    
    # Encrypt credit card
    if 'credit_card' in data:
        encrypted['credit_card'] = await encrypt_field(data['credit_card'])
    
    # Encrypt passport
    if 'passport_number' in data:
        encrypted['passport_number'] = await encrypt_field(data['passport_number'])
    
    return encrypted
```

---

## 🌐 Network Security

### 1. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (change default port)
sudo ufw allow 2222/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow MongoDB (only from app servers)
sudo ufw allow from 10.0.1.0/24 to any port 27017

# Enable firewall
sudo ufw enable
```

### 2. Rate Limiting (Nginx)
```nginx
# Define rate limit zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

server {
    location /api/auth {
        limit_req zone=auth_limit burst=3 nodelay;
        proxy_pass http://backend;
    }
    
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://backend;
    }
}
```

### 3. DDoS Protection (Cloudflare)
```
1. Enable Cloudflare proxy (orange cloud)
2. Set security level to "High"
3. Enable "Under Attack Mode" if needed
4. Configure WAF rules
5. Enable bot protection
```

---

## 🔐 SSL/TLS Configuration

### 1. Let's Encrypt Certificate
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 2. Strong SSL Configuration
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256...';
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

---

## 📝 Logging & Auditing

### 1. Audit Logging
```python
async def log_audit_event(
    user_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict,
    ip_address: str
):
    """Log audit event"""
    await db.audit_logs.insert_one({
        'user_id': user_id,
        'action': action,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'details': details,
        'ip_address': ip_address,
        'user_agent': request.headers.get('User-Agent'),
        'timestamp': datetime.now(timezone.utc)
    })
```

### 2. Security Event Monitoring
```python
# Monitor failed login attempts
failed_login_attempts = defaultdict(int)

async def check_brute_force(email: str, ip: str):
    """Check for brute force attacks"""
    key = f"{email}:{ip}"
    failed_login_attempts[key] += 1
    
    if failed_login_attempts[key] > 5:
        # Block for 1 hour
        await block_ip(ip, duration=3600)
        await send_security_alert(f"Brute force detected: {email} from {ip}")
        return True
    
    return False
```

---

## 🔒 Data Protection

### 1. PII Data Handling
```python
# GDPR compliance
class PersonalData:
    """Handle PII with care"""
    
    @staticmethod
    async def anonymize_guest(guest_id: str):
        """Anonymize guest data (GDPR right to be forgotten)"""
        await db.guests.update_one(
            {'guest_id': guest_id},
            {'$set': {
                'name': 'ANONYMIZED',
                'surname': 'ANONYMIZED',
                'email': f'deleted_{guest_id}@deleted.com',
                'phone': 'DELETED',
                'passport_number': 'DELETED',
                'anonymized_at': datetime.now(timezone.utc)
            }}
        )
    
    @staticmethod
    async def export_personal_data(guest_id: str):
        """Export personal data (GDPR right to data portability)"""
        guest = await db.guests.find_one({'guest_id': guest_id})
        bookings = await db.bookings.find({'guest_id': guest_id}).to_list(None)
        
        return {
            'personal_info': guest,
            'booking_history': bookings,
            'export_date': datetime.now().isoformat()
        }
```

### 2. Data Retention Policy
```python
# Auto-delete old data
async def cleanup_old_data():
    """Clean up data per retention policy"""
    
    # Delete old audit logs (2 years)
    cutoff = datetime.now(timezone.utc) - timedelta(days=730)
    await db.audit_logs.delete_many({'timestamp': {'$lt': cutoff}})
    
    # Anonymize old guest data (5 years)
    cutoff = datetime.now(timezone.utc) - timedelta(days=1825)
    old_guests = await db.guests.find({
        'last_stay': {'$lt': cutoff},
        'anonymized_at': {'$exists': False}
    }).to_list(None)
    
    for guest in old_guests:
        await PersonalData.anonymize_guest(guest['guest_id'])
```

---

## 🚨 Incident Response

### 1. Security Incident Checklist
```markdown
1. [ ] Identify the incident
2. [ ] Contain the threat
3. [ ] Assess the damage
4. [ ] Notify affected users (if PII exposed)
5. [ ] Patch vulnerability
6. [ ] Document incident
7. [ ] Review and improve
```

### 2. Automated Alerts
```python
async def send_security_alert(message: str, severity: str = "high"):
    """Send security alert"""
    # Email
    await send_email(
        to="security@hotelpm s.com",
        subject=f"[SECURITY-{severity.upper()}] {message}",
        body=f"Security alert at {datetime.now()}: {message}"
    )
    
    # Slack
    await send_slack_message(
        channel="#security-alerts",
        message=f"🚨 {message}"
    )
    
    # Log
    logger.critical(f"SECURITY ALERT: {message}")
```

---

## ✅ Security Checklist

### Pre-Production
- [ ] All secrets in environment variables
- [ ] Strong passwords enforced
- [ ] JWT tokens with short expiration
- [ ] HTTPS enabled
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL/NoSQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Database authentication enabled
- [ ] Sensitive data encrypted
- [ ] Audit logging enabled
- [ ] Error messages don't leak info

### Post-Production
- [ ] Regular security updates
- [ ] Monitor audit logs
- [ ] Review access logs
- [ ] Test backups regularly
- [ ] Conduct security audits
- [ ] Train team on security
- [ ] Incident response plan ready
- [ ] Compliance checks (PCI-DSS, GDPR)

---

## 🛠️ Security Tools

### 1. Vulnerability Scanning
```bash
# OWASP ZAP
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://yourdomain.com

# Nmap
nmap -sV -sC yourdomain.com

# SSL Test
sslscan yourdomain.com
```

### 2. Dependency Scanning
```bash
# Python
pip install safety
safety check

# Node.js
npm audit
yarn audit
```

### 3. Code Security Analysis
```bash
# Bandit (Python)
pip install bandit
bandit -r backend/

# ESLint (JavaScript)
npx eslint frontend/src --ext .js,.jsx
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-20  
**Status**: Critical - Must Implement ⚠️
