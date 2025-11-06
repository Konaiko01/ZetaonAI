from abc import ABC, abstractmethod

class IAgent(ABC): 

    @property
    @abstractmethod
    def model()-> str:...

    @property
    @abstractmethod
    def instructions()-> dict:...

    @property
    @abstractmethod
    def input()-> list[dict]:...
    