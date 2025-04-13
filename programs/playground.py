import openai
import os
import dotenv

dotenv.load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "contnt": "Hello, world!"}],
    )
    print(response)
except Exception as e:
    print(e)

