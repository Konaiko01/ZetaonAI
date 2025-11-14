from utils.logger import logger
import requests
import os


class GroupClient:
    """Cliente para gerenciar grupos via Evolution API."""

    def __init__(self):
        self._EVOLUTION_URL = os.getenv("EVOLUTION_URL") or os.getenv("evolution_url")
        self._EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") or os.getenv("evolution_token")

    def get_group_participants(self, group_jid: str, instance: str = "default") -> list[dict]:
        """Buscar lista de participantes de um grupo.

        Args:
            group_jid: JID do grupo (ex: 120363295648424210@g.us)
            instance: ID da instância da Evolution (padrão: default)

        Returns:
            Lista de dicts com id e admin status, ou lista vazia se erro
        """
        try:
            logger.info(f"Buscando participantes do grupo {group_jid}")

            url = f"{self._EVOLUTION_URL.rstrip('/')}/group/participants/{instance}"

            headers = {
                'Content-Type': 'application/json',
                'apikey': self._EVOLUTION_API_KEY,
            }

            params = {
                'groupJid': group_jid
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            participants = data.get('participants', [])

            logger.info(f"Encontrados {len(participants)} participantes no grupo {group_jid}")
            return participants

        except requests.exceptions.RequestException as e:
            logger.error(f'[GroupClient] Erro ao buscar participantes: {e}')
            return []
        except Exception as e:
            logger.error(f"[GroupClient] Erro inesperado: {e}")
            return []

    def get_all_groups(self, instance: str = "default") -> list[dict]:
        """Buscar lista de todos os grupos.

        Args:
            instance: ID da instância da Evolution (padrão: default)

        Returns:
            Lista de dicts com informações dos grupos
        """
        try:
            logger.info("Buscando todos os grupos")

            url = f"{self._EVOLUTION_URL.rstrip('/')}/group/fetchAllGroups/{instance}"

            headers = {
                'Content-Type': 'application/json',
                'apikey': self._EVOLUTION_API_KEY,
            }

            params = {
                'getParticipants': 'true'
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            groups = response.json()
            logger.info(f"Encontrados {len(groups)} grupos")
            return groups

        except requests.exceptions.RequestException as e:
            logger.error(f'[GroupClient] Erro ao buscar grupos: {e}')
            return []
        except Exception as e:
            logger.error(f"[GroupClient] Erro inesperado: {e}")
            return []
