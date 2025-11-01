class ICalendar(ABC):
    
    @abstractmethod
    def create_event(self, event: dict):
        pass

    @abstractmethod
    def get_events(self):
        pass

    @abstractmethod
    def update_event(self):
        pass

    @abstractmethod
    def delete_events(self):
        pass


    
