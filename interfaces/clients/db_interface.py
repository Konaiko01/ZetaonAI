from abc import ABC, abstractmethod

class IDB:
    @abstractmethod
    def add_query(self): ...

    @abstractmethod
    def select_query(self)-> list[dict]: ...

    @abstractmethod
    def delete_query(self): ...

    @abstractmethod
    def collection_exists(self)-> bool: ...