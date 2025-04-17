import openai
import os
import dotenv
import pprint as pp
import logging

dotenv.load_dotenv()

logging.basicConfig(level=logging.DEBUG)

client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
    temperature=None,
)

pp.pprint(response.model_dump())
