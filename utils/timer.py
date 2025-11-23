import time

class Timer:
    def __init__(self, duration=0):
        self.duration = duration
        self.start_time = time.time()

    def set_duration(self, duration):
        self.duration = duration
        self.start_time = time.time()

    def is_finished(self):
        return time.time() - self.start_time >= self.duration

    def reset(self):
        self.start_time = time.time()