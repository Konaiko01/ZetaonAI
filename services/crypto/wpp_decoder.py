import io
import hashlib
import hmac
import base64
import logging
from Crypto.Cipher import AES
from typing import Optional, Dict, Union
logger = logging.getLogger(__name__)


#--------------------------------------------------------------------------------------------------------------------#
class Decoder:
#--------------------------------------------------------------------------------------------------------------------#


    _APP_INFO: Dict[str, bytes] = {
        "image": b"WhatsApp Image Keys",
        "video": b"WhatsApp Video Keys",
        "audio": b"WhatsApp Audio Keys",
        "document": b"WhatsApp Document Keys",
        "audio/ogg": b"WhatsApp Audio Keys",
    }
    
    _EXTENSAO: Dict[str, str] = {
        "image": "jpg",
        "video": "mp4",
        "audio": "ogg",
        "document": "bin",
    }


#--------------------------------------------------------------------------------------------------------------------#


    @staticmethod
    def _derivar_chave_hkdf(chave: bytes, tamanho: int, info_app: bytes = b"") -> bytes:
        chave_hkdf = hmac.new(b"\0" * 32, chave, hashlib.sha256).digest()
        fluxo_chave = b""
        bloco_chave = b""
        indice_bloco = 1
        while len(fluxo_chave) < tamanho:
            bloco_chave = hmac.new(
                chave_hkdf,
                msg=bloco_chave + info_app + (chr(indice_bloco).encode("utf-8")),
                digestmod=hashlib.sha256
            ).digest()
            indice_bloco += 1
            fluxo_chave += bloco_chave
        return fluxo_chave[:tamanho]
    

#--------------------------------------------------------------------------------------------------------------------#


    @staticmethod
    def _remover_padding_aes(dados: bytes) -> bytes:
        tamanho_padding = dados[len(dados) - 1]
        return dados[:-tamanho_padding]
    

#--------------------------------------------------------------------------------------------------------------------#


    @staticmethod
    def _descriptografar_aes(chave: bytes, texto_cifrado: bytes, iv: Optional[bytes]) -> bytes:
        try:
            cipher = AES.new(chave, AES.MODE_CBC, iv)
            texto_plano: bytes = cipher.decrypt(texto_cifrado)
            return Decoder._remover_padding_aes(texto_plano)
        except Exception as e:
            raise ValueError(f"Erro na descriptografia AES: {e}")
        

#--------------------------------------------------------------------------------------------------------------------#


    def decodificar_buffer(self, 
                           buffer_criptografado: io.BytesIO, 
                           chave_midia_base64: str, 
                           mime_type: str) -> io.BytesIO:
        
        try:
            dados_midia: bytes = buffer_criptografado.getvalue()
            chave_midia_bytes: bytes = base64.b64decode(chave_midia_base64)

            info_app = self._APP_INFO.get(mime_type, self._APP_INFO["audio"])
            chave_expandida: bytes = self._derivar_chave_hkdf(chave_midia_bytes, 112, info_app)
            
            # Remove os 10 bytes de autenticação do final do arquivo.
            texto_cifrado: bytes = dados_midia[:-10]
            
            # Key: [16:48] (32 bytes); IV: [:16] (16 bytes)
            dados_decodificados: bytes = self._descriptografar_aes(
                chave=chave_expandida[16:48], 
                texto_cifrado=texto_cifrado, 
                iv=chave_expandida[:16]
            )

            buffer_decodificado = io.BytesIO(dados_decodificados)
            
            extensao = self._EXTENSAO.get(mime_type, mime_type.split("/")[-1])
            buffer_decodificado.name = f"audio_decodificado.{extensao}"
            buffer_decodificado.seek(0)
            
            return buffer_decodificado

        except Exception as e:
            logger.error(f"Falha crítica na decodificação da mídia: {e}")
            raise RuntimeError("Não foi possível decodificar o áudio. Chave ou formato inválido.")
        
#--------------------------------------------------------------------------------------------------------------------#