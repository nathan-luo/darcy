# ======================================
# Import
# ======================================

import os
from dataclasses import dataclass
from datetime import date
from typing import NewType, Optional

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
    name: str
    discord_id: discord_id_type
    notion_id: notion_id_type


# ======================================
# CONSTANTS
# ======================================

# keep column names as constants as these are shared across requests
# and can change

PROJECT_NAME_PROPERTY = "Name"
TASK_NAME_PROPERTY = "Name"
TASKS_FOR_PROJECT_PROPERTY = "Tasks for Project"
TASK_DUE_DATE_PROPERTY = "Date"
TASK_IN_CHARGE_PROPERTY = "In Charge"

# while on discord it is obvious that the chatbot has sent a message,
# notion doesn't have the same system, so it's important to see what darcy has done
CHATBOT_FINGERPRINT = ">DarcyBotWasHere<"

# ======================================
# ENVIRONMENT VARIABLES WITH TYPES
# ======================================

load_dotenv()

# AI: Convert environment variable to proper type after validation
NOTION_API_KEY: notion_api_key_type = notion_api_key_type(os.getenv("NOTION_API_KEY", ""))
if not NOTION_API_KEY:
    raise ValueError("NOTION_API_KEY environment variable is not set")

NOTION_CLIENT: notion_client.Client = notion_client.Client(auth=NOTION_API_KEY)


# ---------------------
# projects vs tasks
# testing vs production
# ---------------------

NOTION_PRODUCTION_DATABASE_ID_TASKS: notion_database_id_type = notion_database_id_type(
    "ed8ba37a719a47d7a796c2d373c794b9"
)
NOTION_PRODUCTION_DATABASE_ID_PROJECTS: notion_database_id_type = notion_database_id_type(
    "918affd4ce0d4b8eb7604d972fd24826"
)

# ---------------------

NOTION_DATABASE_MEMBERS: notion_database_id_type = notion_database_id_type(
    "f56fb0218a4b41718ac610e6f1aa06cb"
)


# ======================================
# Functions - get user ids
# ======================================


def get_user_ids() -> None:
    print(NOTION_CLIENT.users.list())
    print(NOTION_CLIENT.databases.retrieve(database_id=NOTION_DATABASE_MEMBERS))

    # then just ask gtp to extract
    # "Give me a list of names to client ids in this notion json : "


# get_user_ids()

# TODO
name_to_id = {
    "Kevin Tang": "5ed4a4e5-9626-4307-b032-1b530b8ebb1e",
    "Danielle Tran": "8b352898-aa01-40c8-b813-1d674666ebe5",
    "Aopeng Wang": "46899360-7bb6-4578-af49-1e76ff6cbfdc",
    "Nathan Luo": "f746733c-66cc-4cbc-b553-c5d3f03ed240",
    "Anton Huynh": "72af2773-0463-4d0e-bb5d-c6da6d595358",
    "Natalie": "f5f78dd1-365c-4db2-9f40-457821e52e89",
    "Simon Nguyen": "cb1ca5d0-944a-462a-b18a-e7686dfa1a08",
    "Teresa Guo": "f79ec109-12fa-4ae0-8a6f-f57d78e015d3",
    "Soaham": "fffb7e1b-36c2-479a-9571-27a24079fde2",
    "Ryan Li": "4b4523a2-a2f9-4ed8-9520-310cb0ef9dd4",
    "RANIA": "b8ce8d09-0dfd-4560-8a05-883249cce948",
    "Michael Ren": "314ad6eb-dc2e-49b5-8801-4afa0360f39b",
    "Hanshi Tang": "4cb601a8-1375-4e87-832a-fcef5fd7cd96",
    "Hannah": "84fa5ffe-2848-48f5-b3d7-21269c644d5c",
    "Dhruv Ajay": "302a361d-511f-44ba-a728-6cae0661e899",
    "Daksh Agrawal": "427d1cc8-6a68-406b-8397-28aca933609f",
    "Ayushi Chauhan": "7dc516f9-25db-4aed-88de-54255d8f250a",
    "Angus Chan": "ce23a115-7514-474e-9b12-7a99a7699dfe",
    "Ameya Mahesh": "9f52eb8c-690a-44cf-9562-6701fe5b70ab",
    "Elyse Lee": "0cd789b6-1545-459a-bc05-1ec885b14ee1",
    "Avnee": "f5bd1f29-144a-4491-8a21-c283a2b9160c",
    "Brian King": "26ea303a-2f37-49f9-8a5b-42c5ca635cf9",
    "Charmaine": "eefee9b7-e2e1-43aa-95ee-8b224510114a",
    "Clement Chau": "23fc1ca8-785b-4951-8ea5-347432175865",
    "Hayden Ma": "74c1fb03-539a-4de4-8eb1-38492cbeb143",
    "Jake": "1a50bf15-9932-4b7c-8003-776950d5821e",
    "Jamie Marks": "0e36fbe3-66f3-484b-922c-ac8c0bca47b6",
    "Lawrence": "ffb0a19b-0b2f-4b2d-9e97-5f9d35109bb3",
    "Nam Le": "55860929-ef83-408c-b4ae-8ee3d8a8bedd",
    "Nick Muir": "d9e67f1e-b37c-4bf8-9ab9-81e4a78ecfbc",
    "Paul Su": "eddb1224-a77e-4aeb-8ca5-6e5be6e5ef8f",
    "Ruby Nguyen": "c3185939-1d7b-4bb5-af3e-bc7534b1ce0c",
    "Stanley": "1bbd872b-594c-8198-b16d-00029b7b516a",
    "Yiwen Zhang": "1bbd872b-594c-8123-a9c8-0002e6ee833b",
    "Aishwary Shree": "1bbd872b-594c-813e-86da-0002cd09543b",
    "Shayomi": "1bbd872b-594c-816b-b37d-000274bbfbe2",
    "Antoine": "1bbd872b-594c-81f5-bc03-0002a7229ca6",
    "lorraine sanares": "1bbd872b-594c-816f-b62c-000253e00baa",
    "Alina": "1bbd872b-594c-81e9-a745-000238c87ef8",
    "Liao Ziang": "1bbd872b-594c-8160-8126-00029d7b0a08",
    "Henry Routson": "149d872b-594c-8184-ba71-00021997dcb9",
    "Pranav Jayanty": "c005948c-9115-4a4d-b3c2-78286fa75fdb",
    "Pavan Dev": "1bbd872b-594c-8100-aead-00026f26d36d",
    "Lachlan Chue": "1bbd872b-594c-81a3-b7d2-0002e41f8537",
    "Addie Nguyen": "1bbd872b-594c-813f-88ba-00022d2ea8d8",
    "Jiacheng Zheng": "1bbd872b-594c-8172-9c64-0002867fd2c9",
    "Anthea Lee": "1bad872b-594c-81bb-95f1-00025ff97f57",
    "Dhruv Verma": "1bad872b-594c-8110-91e2-0002c091f384",
    "Frank Ngo": "1bbd872b-594c-815a-a001-000245072ba6",
    "Carmen Wong": "1bad872b-594c-817c-aa7b-000212ba08a1",
    "Zim": "1bbd872b-594c-8159-9858-000210dbca44",
    "Eric He": "1bad872b-594c-8129-89c2-0002ee1ba61e",
    "Damien Trinh": "1bbd872b-594c-81b7-bb3d-00020c61fc37",
    "Keith Howen": "1bbd872b-594c-815b-b5f2-0002f50ecfe5",
    "Chi Nguyen": "1bbd872b-594c-81c6-9711-00027493224c",
    "Eddie Li": "1bbd872b-594c-818b-8142-00022dae03c4",
    "Rudra Tiwari": "1bbd872b-594c-8167-b7bb-000231b0eaa5",
}


# ======================================
# Functions - helpers
# ======================================


def get_properties_of_database(database_id: notion_database_id_type) -> list[str]:
    # AI: Get properties of a database
    database = NOTION_CLIENT.databases.retrieve(database_id=database_id)
    return database["properties"].keys()


print(get_properties_of_database(NOTION_PRODUCTION_DATABASE_ID_TASKS))


# ======================================
# Functions - tasks api
# ======================================


class NotionTaskAPI:
    def __init__(
        self,
        tasks_database_id: notion_database_id_type,
        projects_database_id: notion_database_id_type,
    ):
        self.client = NOTION_CLIENT
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
        client.databases.retrieve(database_id=database_id)
        print("Database ID is valid")  # if throws no error
        # print(database)

    # TODO add args
    def create_project(self, project_name: str) -> None:
        """
        Create a project in the projects database
        """

        self.client.pages.create(
            parent={"database_id": self.projects_database_id},
            properties={
                PROJECT_NAME_PROPERTY: {"title": [{"text": {"content": project_name}}]}
            },
        )

    @staticmethod
    def remove_dashes(id_with_dashes: str) -> str:
        # url has no dashes, but the id has them
        return id_with_dashes.replace("-", "")

    def get_all_tasks(self) -> list[notion_task_id_type]:
        """
        Get all tasks from the tasks database
        """

        response = self.client.databases.query(database_id=self.tasks_database_id)

        tasks = response.get("results", [])

        return [notion_task_id_type(task["id"]) for task in tasks]

    def get_tasks(
        self, userID_inCharge: UserID_type, notion_project_id: notion_project_id_type
    ) -> list[notion_task_id_type]:
        """
        Get all tasks from the tasks database
        with provided filters
        """

        # filter by Project AND UserID
        filter_obj = {
            "and": [
                {
                    "property": "Event/Project",
                    "relation": {"contains": notion_project_id},
                },
                {
                    "property": "In Charge",
                    "people": {"contains": userID_inCharge.notion_id},
                },
            ]
        }

        # quering Task database
        response = self.client.databases.query(
            database_id=self.tasks_database_id,
            filter=filter_obj,  # should database id be notion_project_id?
        )
        tasks = response.get("results", [])

        task_ids: list[notion_task_id_type] = [
            notion_task_id_type(task["id"]) for task in tasks
        ]  # tasks are random json
        # TODO how to just request ids without other data?
        return task_ids

    def update_task(
        self,
        notion_task_id: notion_task_id_type,
        notion_progress: notion_progress_type,
        task_name: Optional[str] = None,
        task_due_date: Optional[date] = None,
        task_in_charge: Optional[list[UserID_type]] = None,
        task_event_project: Optional[notion_project_id_type] = None,
    ) -> None:
        """
        Update a task in the tasks database
        """

        print(
            notion_task_id,
            notion_progress,
            task_name,
            task_due_date,
            task_in_charge,
            task_event_project,
        )

        pass

    def get_active_projects(self) -> list[notion_project_id_type]:
        """
        Get all active projects from the projects database
        """

        response = self.client.databases.query(
            database_id=self.projects_database_id,
            # TODO filter based on active
            filter={
                "or": [
                    {"property": "Progress", "select": {"equals": "On-Going"}},
                    {"property": "Progress", "select": {"equals": "In-Progress"}},
                ]
            },
        )

        projects: list[notion_project_id_type] = []

        # AI: Process results ignoring typing issues for now
        try:
            for page in response["results"]:
                project_id = notion_project_id_type(page["id"])
                projects.append(project_id)
        except (KeyError, TypeError) as e:
            print(f"Error processing Notion API response: {e}")

        # TODO is this a correct ID?
        # This is what the url is 1c8c2e93a41280808718ef53e0144f87?v=1c8c2e93a4128012bf84000ceefaeedb
        # This is is returned by the function 1c8c2e93-a412-805e-a263-efad29cd7a2f

        # naurrr isn't it supposed to be 1c8c2e93a41280808718ef53e0144f87

        return projects

    def create_task(
        self,
        task_name: str,
        due_date: date,
        userID: UserID_type,  # TODO change to a list
        # TODO add more
    ) -> None:
        # AI: Create a new task in the Notion database with the given parameters
        self.client.pages.create(
            parent={"database_id": self.tasks_database_id},
            properties={
                TASK_NAME_PROPERTY: {"title": [{"text": {"content": task_name}}]},
                TASK_DUE_DATE_PROPERTY: {"date": {"start": due_date.isoformat()}},
                TASK_IN_CHARGE_PROPERTY: {
                    "people": [{"object": "user", "id": userID.notion_id}]
                },
            },
        )


# Basic testing


henryID = UserID_type(
    name="Henry",
    discord_id=discord_id_type("872718183692402688"),
    notion_id=notion_id_type("149d872b-594c-8184-ba71-00021997dcb9"),
)

notion_api_production = NotionTaskAPI(
    tasks_database_id=NOTION_PRODUCTION_DATABASE_ID_TASKS,
    projects_database_id=NOTION_PRODUCTION_DATABASE_ID_PROJECTS,
)

# notion_api_production.create_task(
#     task_name="Test Task" + CHATBOT_FINGERPRINT,
#     due_date=date(2025, 1, 1),
#     userID=henryID,
# )

projects: list[notion_project_id_type] = notion_api_production.get_active_projects()
print("projects ", projects)
tasks: list[notion_task_id_type] = notion_api_production.get_all_tasks()
print("tasks ", tasks)


# notion_api_production.create_project(project_name="Test Project" + CHATBOT_FINGERPRINT)

# get the tasks for each project
for proj in projects:
    tasks: list[notion_task_id_type] = notion_api_production.get_tasks(
        userID_inCharge=henryID, notion_project_id=proj
    )
    print("proj ============", proj)
    print("tasks", tasks)
