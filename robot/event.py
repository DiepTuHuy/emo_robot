from enum import Enum, auto

class RobotEvent(Enum):
    FACE_DETECTED = auto()
    FACE_LOST = auto()
    VOICE_COMMAND = auto()

class EventManager:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, event_type: RobotEvent, handler):
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        
    def publish(self, event_type: RobotEvent, data=None):
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                handler(event_type, data)