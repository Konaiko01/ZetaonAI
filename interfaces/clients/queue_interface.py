from abc import ABC,abstractmethod

class IQueue:

    @abstractmethod
    def create_queue(self): ...

    @abstractmethod
    def read_queue(self)->list[dict]: ...

    @abstractmethod
    def del_queue(self): ...

    @abstractmethod
    def update_queue(self): ...
