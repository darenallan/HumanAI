"""
crypto.py
---------
Module de chiffrement symétrique AES-256.
Utilisé pour chiffrer les documents générés et les données ultra-sensibles
avant leur insertion en base de données.
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config.config import settings

# On utilise la clé définie dans settings (DB_ENCRYPTION_KEY)
# Si elle n'est pas définie ou de mauvaise taille, on génère une clé temporaire (dev only)
try:
    if settings.DB_ENCRYPTION_KEY:
        _key = base64.urlsafe_b64decode(settings.DB_ENCRYPTION_KEY)
        if len(_key) not in (16, 24, 32):
            raise ValueError("Clé de taille invalide")
    else:
        raise ValueError("Clé absente")
except Exception:
    # Pour le développement local si aucune clé valide n'est fournie
    _key = AESGCM.generate_key(bit_length=256)


def encrypt_data(plaintext: str) -> str:
    """
    Chiffre une chaîne de caractères en AES-256-GCM.
    Retourne le nonce + ciphertext encodé en base64 urlsafe.
    """
    aesgcm = AESGCM(_key)
    nonce = os.urandom(12)  # Recommandation GCM: 96 bits
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    # On concatène le nonce et le texte chiffré pour le décodage ultérieur
    encrypted_blob = nonce + ciphertext
    return base64.urlsafe_b64encode(encrypted_blob).decode("utf-8")


def decrypt_data(encrypted_b64: str) -> str:
    """
    Déchiffre une chaîne chiffrée par encrypt_data.
    """
    try:
        encrypted_blob = base64.urlsafe_b64decode(encrypted_b64)
        nonce = encrypted_blob[:12]
        ciphertext = encrypted_blob[12:]
        
        aesgcm = AESGCM(_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Erreur de déchiffrement: {e}")
