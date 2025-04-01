type person_id = str
type project_id = str
type task_id = str
type progress = str
type date = str


def create_filter_object_(
    *properties,
):  # for each database # Figure out the Filter Object Syntax
    pass


def get_tasks(person_id, project_id):  # Function to read tasks from projects database
    pass


def update_task(task_id, progress, date, person):  # Function to update tasks
    pass


def todo():  # Be able to update a field with a specific user
    pass


def get_active_projects():  # -> Parsed list of project ids and project names # Function to query active project
    pass


def create_task(task_name, due_date, person_id, project_id):  # Function to create tasks
    pass
