import os

import notion_client

type person_id_type = str
type project_id_type = str
type task_id_type = str
type progress_type = str
type date_type = str


class NotionTaskAPI:
    def __init__(self):
        self.client = notion_client.Client(auth=os.getenv("NOTION_API_KEY"))

    def create_filter_object_(self):
        # for each database # Figure out the Filter Object Syntax
        pass

    def get_tasks(self, person_id: person_id_type, project_id: project_id_type):
        # Function to read tasks from projects database
        print(person_id, project_id)
        pass

    def update_task(
        self,
        task_id: task_id_type,
        progress: progress_type,
        date: date_type,
        person: person_id_type,
    ):
        # Function to update tasks
        print(task_id, progress, date, person)
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
        due_date: date_type,
        person_id: person_id_type,
        project_id: project_id_type,
    ):
        # Function to create tasks
        print(task_name, due_date, person_id, project_id)
        pass
