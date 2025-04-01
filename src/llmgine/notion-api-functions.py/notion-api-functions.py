# ======================================
# Import
# ======================================


import os
from dataclasses import dataclass
from datetime import date

import notion_client

# ======================================
# Types
# ======================================


type user_name_type = str
type discord_id_type = str
type notion_id_type = str
type notion_project_id_type = str
type notion_task_id_type = str
type notion_progress_type = str


# an ID structs which contains all types of userids


@dataclass
class UserID_type:
    discord_id: discord_id_type
    notion_id: notion_id_type


class NotionTaskAPI:
    def __init__(self):
        self.client = notion_client.Client(auth=os.getenv("NOTION_API_KEY"))

    def create_filter_object_(self):
        # for each database # Figure out the Filter Object Syntax
        pass

    def get_tasks(self, userID: UserID_type, notion_project_id: notion_project_id_type):
        # Function to read tasks from projects database
        print(userID, notion_project_id)
        pass

    def update_task(
        self,
        notion_task_id: notion_task_id_type,
        notion_progress: notion_progress_type,
        date: date,
        userID: UserID_type,
    ):
        # Function to update tasks
        print(notion_task_id, notion_progress, date, userID)
        pass

    def todo(self):
        # Be able to update a field with a specific user
        pass

    def get_active_projects(self):
        # -> Parsed list of project ids and project names # Function to query active project
        pass

    def create_task(
        self,
        task_name: str,
        due_date: date,
        userID: UserID_type,
        notion_project_id: notion_project_id_type,
    ):
        # Function to create tasks
        print(task_name, due_date, userID, notion_project_id)
        pass


# Basic testing

henryID = UserID_type(discord_id="1234567890", notion_id="1234567890")
