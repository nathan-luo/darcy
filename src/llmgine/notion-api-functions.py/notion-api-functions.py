# ======================================
# Import
# ======================================

import os
from dataclasses import dataclass
from datetime import date
from typing import NewType

import notion_client
from dotenv import load_dotenv

# ======================================
# Types
# ======================================

# AI: Using NewType to create distinct types that can't be implicitly converted
user_name_type = NewType("user_name_type", str)
discord_id_type = NewType("discord_id_type", str)
notion_id_type = NewType("notion_id_type", str)
notion_database_id_type = NewType("notion_database_id_type", str)
notion_project_id_type = NewType("notion_project_id_type", str)
notion_task_id_type = NewType("notion_task_id_type", str)
notion_progress_type = NewType("notion_progress_type", str)
notion_api_key_type = NewType("notion_api_key_type", str)


@dataclass
class UserID_type:
    discord_id: discord_id_type
    notion_id: notion_id_type


# ======================================
# ENVIRONMENT VARIABLES WITH TYPES
# ======================================

load_dotenv()

# AI: Convert environment variable to proper type after validation
NOTION_API_KEY: notion_api_key_type = notion_api_key_type(os.getenv("NOTION_API_KEY", ""))
if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY environment variable is not set")


# ---------------------
# projects vs tasks
# testing vs production
# ---------------------


NOTION_TESTING_DATABASE_ID_TASKS: notion_database_id_type = notion_database_id_type(
    os.getenv("NOTION_TESTING_DATABASE_ID_TASKS", "")
)
if not NOTION_TESTING_DATABASE_ID_TASKS:
    raise ValueError("NOTION_TESTING_DATABASE_ID_TASKS environment variable is not set")

NOTION_TESTING_DATABASE_ID_PROJECTS: notion_database_id_type = notion_database_id_type(
    os.getenv("NOTION_TESTING_DATABASE_ID_PROJECTS", "")
)
if not NOTION_TESTING_DATABASE_ID_PROJECTS:
    raise ValueError(
        "NOTION_TESTING_DATABASE_ID_PROJECTS environment variable is not set"
    )

NOTION_PRODUCTION_DATABASE_ID_TASKS: notion_database_id_type = notion_database_id_type(
    os.getenv("NOTION_PRODUCTION_DATABASE_ID_TASKS", "")
)
if not NOTION_PRODUCTION_DATABASE_ID_TASKS:
    raise ValueError(
        "NOTION_PRODUCTION_DATABASE_ID_TASKS environment variable is not set"
    )

NOTION_PRODUCTION_DATABASE_ID_PROJECTS: notion_database_id_type = notion_database_id_type(
    os.getenv("NOTION_PRODUCTION_DATABASE_ID_PROJECTS", "")
)
if not NOTION_PRODUCTION_DATABASE_ID_PROJECTS:
    raise ValueError(
        "NOTION_PRODUCTION_DATABASE_ID_PROJECTS environment variable is not set"
    )


# ======================================
# Functions
# ======================================


class NotionTaskAPI:
    def __init__(
        self,
        tasks_database_id: notion_database_id_type,
        projects_database_id: notion_database_id_type,
    ):
        self.client = notion_client.Client(auth=NOTION_API_KEY)
        self.tasks_database_id = tasks_database_id
        self.projects_database_id = projects_database_id

        self.validate_database_id(client=self.client, database_id=self.tasks_database_id)
        self.validate_database_id(
            client=self.client, database_id=self.projects_database_id
        )

    @staticmethod
    def validate_database_id(
        client: notion_client.Client, database_id: notion_database_id_type
    ):
        # AI: fetch database to validate it exists and we have access
        database = client.databases.retrieve(database_id=database_id)
        print("Database ID is valid")
        print(database)

    def get_tasks(
        self, userID: UserID_type, notion_project_id: notion_project_id_type
    ) -> list[notion_task_id_type]:
        # Function to read tasks from projects database
        print(userID, notion_project_id)
        return []

    def update_task(
        self,
        notion_task_id: notion_task_id_type,
        notion_progress: notion_progress_type,
        date: date,
        userID: UserID_type,
    ) -> None:
        # Function to update tasks
        print(notion_task_id, notion_progress, date, userID)
        pass

    def get_active_projects(self) -> list[notion_project_id_type]:
        # -> Parsed list of project ids and project names # Function to query active project
        return []

    def create_task(
        self,
        task_name: str,
        due_date: date,
        userID: UserID_type,
    ) -> None:
        pass


# Basic testing


henryID = UserID_type(
    discord_id=discord_id_type("872718183692402688"), notion_id=notion_id_type("")
)

notion_api_testing = NotionTaskAPI(
    tasks_database_id=NOTION_TESTING_DATABASE_ID_TASKS,
    projects_database_id=NOTION_TESTING_DATABASE_ID_PROJECTS,
)

notion_api_testing.create_task(
    task_name="Test Task",
    due_date=date(2025, 1, 1),
    userID=henryID,
)
