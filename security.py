import hashlib
import hmac
import os
import secrets

from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()
password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

def generate_session_token() -> str:
    # This generates a cryptographically secure random token containing 32 bytes of randomness (256 bits).
    return secrets.token_urlsafe(32)

def hash_session_token(token: str) -> str:
    # This produces a hexadecimal SHA-256 hash of the token.
    return hashlib.sha256(token.encode()).hexdigest()

def get_csrf_secret() -> str:
    csrf_secret = os.environ.get("CSRF_SECRET")
    if not csrf_secret:
        raise RuntimeError("The csrf secret is empty or does not exist.")
    return csrf_secret

def generate_csrf_token(session_token: str) -> str:
    csrf_secret = get_csrf_secret()
    byted_csrf_secret = csrf_secret.encode()
    byted_session_token = session_token.encode()
    # HMAC-SHA256: Uses a secret key to authenticate data.
    token = hmac.new(byted_csrf_secret, byted_session_token, hashlib.sha256)
    return token.hexdigest()