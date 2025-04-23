

# This is a file to validate environment variables

import os
import dotenv

dotenv.load_dotenv()

def validate_env_keys() :

  assert(os.getenv("NOT A KEY") == None)

  required_keys = [
    "OPENAI_API_KEY", 
    "OPENROUTER_API_KEY", 
    "NOTION_TOKEN", 
    "NOTION_API_KEY", 
    "NOTION_TESTING_DATABASE_ID", 
    "NOTION_PRODUCTION_DATABASE_ID_TASKS", 
    "NOTION_PRODUCTION_DATABASE_ID_PROJECTS", 
    "TEST_SERVER_ID", 
    "DARCY_KEY", 
    "DARYL_KEY",
  ]


  for key in required_keys :
    val = os.getenv(key)
    if (val == None) :
      raise Exception(f"{key} is not in env keys")

validate_env_keys()