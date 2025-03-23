from llmgine.llm.tools import ToolManager

def get_weather(location: str):
  """
  A test weather tool, returns a random weather.

  Args:
    location: The location to get the weather for.

  """
  return f"The weather in {location} is sunny."
  
tool_manager = ToolManager()
tool_manager.register_tool("get_weather", get_weather)