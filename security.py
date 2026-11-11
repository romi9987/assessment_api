import hashlib
import secrets

from pwdlib import PasswordHash

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