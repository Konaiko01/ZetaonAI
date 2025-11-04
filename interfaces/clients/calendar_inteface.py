from abc import ABC, abstractmethod

'''
Interface com o objetivo de adapatar e abstrair a aplicacao
para que seja possivel usar mais de um cliente(API) de calendario
'''

class ICalendar(ABC):
    #retorna o id do evento criado
    @abstractmethod
    def create_event(self)-> str: ...
    
    #retorna o json com todods os eventos
    @abstractmethod
    def get_events(self)-> str: ...

    #retorna o json com evento do id passado no parametro
    @abstractmethod
    def get_event_by_id(self, id: str)-> str: ...

    #retorna uma boolean que fala se a auteração foi feita
    @abstractmethod
    def update_event(self)-> bool: ...

    #retorna um boolean dizendo se a delete foi bem sucedido
    @abstractmethod
    def delete_events(self)-> bool: ...



    
