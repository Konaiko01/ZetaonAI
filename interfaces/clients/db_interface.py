from abc import ABC, abstractmethod

class IDB(ABC):
    @abstractmethod
    def get_client(self)-> dict | None: ...

    @abstractmethod
    def set_client(self, client:dict)-> bool:...

    @abstractmethod
    def del_client(self,client_id)-> bool: ...
    
    @abstractmethod
    def get_all_context(self)-> list[dict] | None: ...

    @abstractmethod
    def set_new_context(self)-> bool: ...

    @abstractmethod
    def del_contexte(self, client_id, to_be_deleted)-> bool: ...