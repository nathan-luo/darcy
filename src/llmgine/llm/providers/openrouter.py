import openai
import os
class OpenRouterProvider:
    def __init__(self, model: str, provider_name: str):
        self.model = model
        self.provider_name = provider_name
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.client = openai.OpenAI(api_key=self.api_key,
                                    base_url="https://openrouter.ai/api/v1")
    
    def generate(self, ):



class OpenRouterResponse(LLMResponse):
    def __init__(self, response: openai.OpenAI.ChatCompletion):
        self.response = response

    def get_content(self):
        return self.response.choices[0].message.content
