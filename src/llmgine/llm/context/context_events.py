class ContextEvent(Event):
    def __init__(self, session_id: str, engine_id: str, context: List[Dict[str, Any]]):
        super().__init__(session_id=session_id, engine_id=engine_id)
        self.context = context
