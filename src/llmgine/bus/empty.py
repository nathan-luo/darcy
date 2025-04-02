class EmptyBus:
    def __init__(self):
        pass

    def register_command_handler(self, command_type, handler):
        pass

    def register_async_command_handler(self, command_type, handler):
        pass

    def register_event_handler(self, event_type, handler):
        pass

    def register_async_event_handler(self, event_type, handler):
        pass

    async def execute(self, command):
        pass

    async def publish(self, event):
        pass
