"""Cifrado simétrico de secretos guardados en BD (tokens OAuth).

Usa Fernet (AES-128-CBC + HMAC-SHA256). Para generar una clave nueva:
    uv run python -m app.core.crypto
"""

from cryptography.fernet import Fernet, InvalidToken


class TokenCipherError(Exception):
    """El valor cifrado no se puede descifrar (clave distinta o dato corrupto)."""


class TokenCipher:
    def __init__(self, key: str):
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise TokenCipherError("No se pudo descifrar el token.") from exc


if __name__ == "__main__":
    print(Fernet.generate_key().decode())
