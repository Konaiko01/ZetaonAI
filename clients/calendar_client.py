from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from typing import Any, Optional, List, Dict
from utils.logger import logger
import asyncio
import datetime
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

    def _fix_timezone(self, iso_datetime: str) -> str:
        """Adiciona fuso horário UTC (Z) se estiver faltando, para evitar Erro 400."""
        try:
            dt = datetime.datetime.fromisoformat(iso_datetime)
            if dt.tzinfo is None:
                logger.warning(f"Data {iso_datetime} veio sem fuso. Adicionando UTC ('Z').")
                return iso_datetime + "Z"
            return iso_datetime
        except (ValueError, TypeError):
            logger.error(f"Formato de data inválido recebido: {iso_datetime}")
            # Retorna o original para a API falhar (é melhor do que adivinhar)
            return iso_datetime

#--------------------------------------------------------------------------------------------------------------------#

    async def get_events(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        logger.info(f"[GCalendarClient] Buscando eventos de {start_date} até {end_date}")
        start_date_fixed = self._fix_timezone(start_date)
        end_date_fixed = self._fix_timezone(end_date)
        try:
            events_result = await self._run_blocking_io(
                self._service.events().list(
                    calendarId=self._calendar_id,
                    timeMin=start_date_fixed,
                    timeMax=end_date_fixed,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute
            )
            events = events_result.get("items", [])
            logger.info(f"[GCalendarClient] API do Google retornou {len(events)} eventos.")
            return events
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao buscar eventos: {error}", exc_info=True)
            return [f"Erro ao buscar eventos: {error.reason}"]
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em get_events: {e}", exc_info=True)
            return [f"Erro inesperado: {e}"]
            
#--------------------------------------------------------------------------------------------------------------------#

    async def create_event(self, summary: str, start_time: str, end_time: str) -> Optional[dict[str, Any]]: # <-- Removido 'attendees'
        logger.info(f"[GCalendarClient] Criando evento: '{summary}'")
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': end_time, 'timeZone': 'America/Sao_Paulo'},
        }      
        try:
            created_event = await self._run_blocking_io(
                self._service.events().insert(
                    calendarId=self._calendar_id, 
                    body=event_body,
                    sendNotifications=False
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento criado com sucesso (sem convidados). ID: {created_event.get('id')}")
            return created_event
        except HttpError as error:
            logger.error(f"[GCalendarClient] Erro ao criar evento: {error}", exc_info=True)
            return {"error": f"Erro 403 do Google: {error.reason}"}
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em create_event: {e}", exc_info=True)
            return {"error": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def update_event(self, event_id: str, update_body: Dict[str, Any]) -> Optional[Dict[str, Any]]: 
        logger.info(f"[GCalendarClient] Atualizando evento: {event_id} com body: {update_body}")
        
        try:
            updated_event = await self._run_blocking_io(
                self._service.events().patch(
                    calendarId=self._calendar_id, 
                    eventId=event_id, 
                    body=update_body, 
                    sendNotifications=False
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento '{event_id}' atualizado (patch) com sucesso.")
            return updated_event
            
        except HttpError as error:
             logger.error(f"[GCalendarClient] Erro ao atualizar (patch) evento '{event_id}': {error}", exc_info=True)
             return {"error": f"Erro Http: {error.reason}"}
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em update_event: {e}", exc_info=True)
            return {"error": f"Erro interno: {e}"}

#--------------------------------------------------------------------------------------------------------------------#

    async def delete_event(self, event_id: str) -> bool: 
        logger.info(f"[GCalendarClient] Deletando evento: {event_id}")
        try:
            await self._run_blocking_io(
                self._service.events().delete(
                    calendarId=self._calendar_id,
                    eventId=event_id
                ).execute
            )
            logger.info(f"[GCalendarClient] Evento '{event_id}' deletado com sucesso.")
            return True
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"[GCalendarClient] Evento '{event_id}' já não existia (404).")
                return True
            logger.error(f"[GCalendarClient] Erro Http ao deletar evento '{event_id}': {error}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"[GCalendarClient] Erro inesperado em delete_event: {e}", exc_info=True)
            return False

#--------------------------------------------------------------------------------------------------------------------#