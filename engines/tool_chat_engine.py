import uuid
from llmgine.bus.bus import MessageBus
from llmgine.llm.context.memory import SingleChatContextManager
from llmgine.llm.tools.tool_manager import ToolManager
from openai import OpenAI
from llmgine.messages.commands import Command, CommandResult


class PromptCommand(Command):
    def __init__(self, message: str):
        self.message = message


class ToolChatEngine:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.tool_manager = ToolManager()
        self.context_manager = SingleChatContextManager()
        self.llm = OpenAI()
        self.model = "gpt-4o-mini"
        self.bus = MessageBus()
        self.bus.register_command_handler(PromptCommand, self._handle_prompt)

    def execute(self, message: str) -> str:
        self.context_manager.add_message(message)
        response = self.llm.chat.completions.create(
            model=self.model,
            messages=self.context_manager.get_context(),
            tools=self.tool_manager.get_tools(),
        )
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                self.tool_manager.execute_tool(tool_call)
                self.context_manager.add_tool_result(tool_call)
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=self.context_manager.get_context(),
            )
            return response.choices[0].message.content
        else:
            return response.choices[0].message.content

    def _handle_prompt(self, command: PromptCommand) -> str:
        response = self.execute(command.message)
        command_result = CommandResult(response)
        return command_result
