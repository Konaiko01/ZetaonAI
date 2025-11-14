from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from typing import Any, Optional, List, Dict
from utils.logger import logger
import asyncio

from interfaces.clients.calendar_inteface import ICalendar

#--------------------------------------------------------------------------------------------------------------------#
class GCalendarClient(ICalendar):
#--------------------------------------------------------------------------------------------------------------------#

    SCOPES = ["https://www.googleapis.com/auth/calendar"]

#--------------------------------------------------------------------------------------------------------------------#

    def __init__(self, service_account_info: Dict[str, Any], calendar_id: str):
        if not service_account_info:
            raise ValueError("Credenciais da Conta de Serviço não fornecidas.")
        if not calendar_id:
            raise ValueError("ID da Agenda (GCALENDAR_ID) não fornecido.")
        try:
            self._creds = Credentials.from_service_account_info(
                service_account_info, scopes=self.SCOPES
            )
            self._service = build("calendar", "v3", credentials=self._creds)
            self._calendar_id = calendar_id 
            logger.info(f"[GCalendarClient] Cliente inicializado. Alvo: {self._calendar_id}")
        except Exception as e:
            logger.error(f"[GCalendarClient] Falha ao carregar credenciais: {e}", exc_info=True)
            raise

#--------------------------------------------------------------------------------------------------------------------#

    async def _run_blocking_io(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

#--------------------------------------------------------------------------------------------------------------------#

    async def get_events(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        logger.info(f"[GCalendarClient] Buscando eventos de {start_date} até {end_date}")
        try:
            events_result = await self._run_blocking_io(
                self._service.events().list(
                    calendarId=self._calendar_id,
                    timeMin=start_date,
                    timeMax=end_date,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute
            )
            events = events_result.get("items", [])
            logger.info(f"[GCalendarClient] API do Google retornou {len(events)} eventos.")
            return events
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em get_events: {e}", exc_info=True)
            return [f"Erro ao buscar eventos: {e}"] 
            
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
                    calendarId=self._calendar_id,
                    body=event_body,
                    sendNotifications=False
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento criado com sucesso. ID: {created_event.get('id')}")
            return created_event
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao criar evento: {error}", exc_info=True)
            return {"error": f"Erro 403 do Google: {error.reason}"}
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em create_event: {e}", exc_info=True)
            return {"error": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def get_event_by_id(self, event_id: str) -> Optional[dict[str, Any]]: 
        logger.info(f"[GCalendarClient] Buscando evento por ID: {event_id}")
        try:
            event = await self._run_blocking_io(
                self._service.events().get(
                    calendarId="primary", 
                    eventId=event_id
                ).execute
            )
            return event
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao buscar evento '{event_id}': {error}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em get_event_by_id: {e}", exc_info=True)
            return None

#--------------------------------------------------------------------------------------------------------------------#

    async def update_event(self, event_id: str, event_body: Dict[str, Any]) -> Optional[Dict[str, Any]]: 
        logger.info(f"[GCalendarClient] Atualizando evento: {event_id}")
        try:
            updated_event = await self._run_blocking_io(
                self._service.events().update(
                    calendarId="primary", 
                    eventId=event_id, 
                    body=event_body
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento '{event_id}' atualizado com sucesso.")
            return updated_event
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao atualizar evento '{event_id}': {error}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em update_event: {e}", exc_info=True)
            return None

#--------------------------------------------------------------------------------------------------------------------#

    async def delete_event(self, event_id: str) -> bool: 
        logger.info(f"[GCalendarClient] Deletando evento: {event_id}")
        try:
            await self._run_blocking_io(
                self._service.events().delete(
                    calendarId="primary", 
                    eventId=event_id
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento '{event_id}' deletado com sucesso.")
            return True
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao deletar evento '{event_id}': {error}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em delete_event: {e}", exc_info=True)
            return False

    async def delete_events(self) -> bool:
        logger.warning("GCalendarClient.delete_events (plural) não é suportado. Use delete_event(event_id).")
        return False