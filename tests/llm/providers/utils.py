import os
import json
from openai.types.chat import ChatCompletion


def get_saved_response(test_name: str, folder_name: str):
    response = None
    if os.path.exists(f"tests/llm/providers/{folder_name}/{test_name}.json"):
        with open(f"tests/llm/providers/{folder_name}/{test_name}.json", "r") as f:
            response = json.load(f)
    return response


def save_response_chat_completion(
    test_name: str, response: ChatCompletion, folder_name: str
):
    file_path = f"tests/llm/providers/{folder_name}/{test_name}.json"
    if not os.path.exists(file_path):
        # Convert ChatCompletion to a dictionary
        serialized_response = response.model_dump_json()

        with open(file_path, "w") as f:
            f.write(json.dumps(json.loads(serialized_response), indent=4))
