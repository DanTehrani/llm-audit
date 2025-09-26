
from typing import TypedDict

from termcolor import colored
from main import get_entry_point_contract, get_entry_point_functions
import os
import json
import tiktoken

from utils import ProjectToAudit, get_projects

PROJECTS = get_projects()

def get_files_to_audit(dir_path: str, project_name: str):
    files = os.listdir(dir_path)

    file_to_audit = []
    for file in files:
        if file.startswith("I"):
            continue

        print(colored(f"Checking file: {file}", "blue"))

        with open(f"{dir_path}/{file}", "r") as f:
            contract_code = f.read()

        tokenized = tiktoken.encoding_for_model("o3-mini").encode(contract_code)
        contract_code_num_tokens = len(tokenized)

        if contract_code_num_tokens > 100_000:
            continue
    
        entry_point_contract = get_entry_point_contract(os.path.join(dir_path, file), project_name)

        if entry_point_contract is None:
            continue

        entry_point_functions = get_entry_point_functions(entry_point_contract)

        if len(entry_point_functions) > 30:
            continue

        if len(entry_point_functions) == 0:
            continue

        file_to_audit.append(file)

    return file_to_audit




if __name__ == "__main__":
    all_files_to_audit = []

    for project in PROJECTS:
        try:    
            projects_to_audit = get_files_to_audit(f"/Users/danieltehrani/dev/repos/{project}/flattened_with_impls", project)
            print(colored(f"Successfully found {len(projects_to_audit)} files to audit for {project}", "green"))
        except Exception as e:
            print(colored(f"Error getting files to audit for {project}: {e}", "red"))
            continue

        all_files_to_audit.append(ProjectToAudit(project=project, files=projects_to_audit))

    with open("./projects_to_audit.json", "w") as f:
        json.dump(all_files_to_audit, f, indent=4, default=str)
