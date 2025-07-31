import llm

class Memory(llm.Toolbox):
    _memory = None

    def _get_memory(self):
        if self._memory is None:
            self._memory = {}
        return self._memory

    def set(self, key: str, value: str):
        "Set something as a key"
        self._get_memory()[key] = value

    def get(self, key: str):
        "Get something from a key"
        return self._get_memory().get(key) or ""

    def append(self, key: str, value: str):
        memory = self._get_memory()
        memory[key] = (memory.get(key) or "") + "\n" + value

    def keys(self):
        "Return a list of keys"
        return list(self._get_memory().keys())