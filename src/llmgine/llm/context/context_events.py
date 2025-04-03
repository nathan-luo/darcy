class ContextEvent(Event):
    def __init__(
        self,
        context_manager_id: str,
        session_id: str,
        engine_id: str,
        context: List[Dict[str, Any]],
    ):
        super().__init__(session_id=session_id, engine_id=engine_id)
        self.context_manager_id = context_manager_id
        self.context = context


class ContextCompiledEvent(ContextEvent):
    def __init__(
        self,
        context_manager_id: str,
        session_id: str,
        engine_id: str,
        context: List[Dict[str, Any]],
    ):
        super().__init__(context_manager_id, session_id, engine_id, context)
