"""
Classes d'aide pour les tests
"""
import time

class DummyStdout:
    """Classe simulant un stdout itérable avec délai optionnel"""
    def __init__(self, lines, delay=0.01):
        self._lines = lines
        self._delay = delay
        self._index = 0
        self._closed = False
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._index < len(self._lines):
            time.sleep(self._delay)
            line = self._lines[self._index]
            self._index += 1
            return line
        raise StopIteration
    
    def readline(self):
        try:
            return self.__next__()
        except StopIteration:
            return ''
    
    def close(self):
        self._closed = True

class DummyProcess:
    """Mock process class for testing"""
    def __init__(self, output_lines, return_code=0):
        # Rendre stdout directement itérable
        self.stdout = iter(output_lines)
        self._return_code = return_code
        self.pid = 12345
        self.terminated = False
        self.killed = False
    
    def poll(self):
        return None if not self.terminated and not self.killed else self._return_code
    
    def terminate(self):
        self.terminated = True
    
    def kill(self):
        self.killed = True
    
    def wait(self, timeout=None):
        if not self.terminated and not self.killed:
            if timeout:
                raise Exception("Process timeout")
        return self._return_code
    
    def close(self):
        pass
