from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

def _get_fernet() -> Fernet:
    key = settings.FERNET_KEY
    if not key:
        raise RuntimeError('FERNET_KEY 未配置，请在 .env 中设置加密密钥')
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt(plain_text: str) -> str:
    if not plain_text: return ''
    return _get_fernet().encrypt(plain_text.encode('utf-8')).decode('utf-8')

def decrypt(cipher_text: str) -> str:
    if not cipher_text: return ''
    try:
        return _get_fernet().decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception) as e:
        raise ValueError(f'解密失败: {e}')

def generate_key() -> str:
    return Fernet.generate_key().decode('utf-8')
