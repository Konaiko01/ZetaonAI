from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from typing import Any, Optional
from utils.logger import logger
import os.path
import asyncio

#--------------------------------------------------------------------------------------------------------------------#
class GCalendarClient:
#--------------------------------------------------------------------------------------------------------------------#

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, json_keyfile_path: str):
        if not os.path.exists(json_keyfile_path):
            logger.error(f"[GCalendarClient] Arquivo de credenciais não encontrado: {json_keyfile_path}")
            raise FileNotFoundError(f"Arquivo de conta de serviço não encontrado: {json_keyfile_path}")
            
        try:
            self._creds = Credentials.from_service_account_file(
                json_keyfile_path, scopes=self.SCOPES
            )
            self._service = build("calendar", "v3", credentials=self._creds)
            logger.info("[GCalendarClient] Cliente (Conta de Serviço) inicializado.")
        except Exception as e:
            logger.error(f"[GCalendarClient] Falha ao carregar credenciais: {e}", exc_info=True)
            raise

#--------------------------------------------------------------------------------------------------------------------#

    async def _run_blocking_io(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

#--------------------------------------------------------------------------------------------------------------------#

    async def get_events(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        logger.info(f"[GCalendarClient] Buscando eventos de {start_date} até {end_date}")
        try:
            events_result = await self._run_blocking_io(
                self._service.events().list(
                    calendarId="primary",
                    timeMin=start_date,
                    timeMax=end_date,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute
            )
            events = events_result.get("items", [])
            logger.info(f"[GCalendarClient] {len(events)} eventos encontrados.")
            return events
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao buscar eventos: {error}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em get_events: {e}", exc_info=True)
            return []

#--------------------------------------------------------------------------------------------------------------------#

    async def create_event(self, summary: str, start_time: str, end_time: str, attendees: list[str]) -> Optional[dict[str, Any]]:
        logger.info(f"[GCalendarClient] Criando evento: '{summary}'")
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
            'attendees': [{'email': email} for email in attendees],
        }
        try:
            created_event = await self._run_blocking_io(
                self._service.events().insert(
                    calendarId="primary",
                    body=event_body
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento criado com sucesso. ID: {created_event.get('id')}")
            return created_event
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao criar evento: {error}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em create_event: {e}", exc_info=True)
            return None