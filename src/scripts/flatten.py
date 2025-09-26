import os
from termcolor import colored
import subprocess
from utils import get_files_in_scope

def flatten_repo(repo_full_path: str):
    files = get_files_in_scope(repo_full_path)
    output_dir_full_path = f"{repo_full_path}/flattened"

    for file in files:
        file_full_path = os.path.normpath(f"{repo_full_path}/{file}")
        output_file_name = file.split("/")[-1].replace(".sol", ".flattened.sol")
        output_full_path = f"{output_dir_full_path}/{output_file_name}"

        result = subprocess.run(
            f"forge flatten --root {repo_full_path} {file_full_path} > {output_full_path}",
            capture_output=True,   # capture stdout/stderr
            shell=True,
            text=True              # decode bytes → str
        )

        print(result.stdout, result.stderr)


def check_flattened_repo(repo_full_dir_path: str):
    flattened_files = os.listdir(f"{repo_full_dir_path}/flattened")

    files_in_scope = get_files_in_scope(repo_full_dir_path)

    for file in files_in_scope:
        expected_file_name = file.split("/")[-1].replace(".sol", ".flattened.sol")
        if expected_file_name not in flattened_files:
            print(colored(f"File {file} not found in {repo_full_dir_path}/flattened", "red"))
            return False

    return True

REPOS_PATH = "/Users/danieltehrani/dev/repos"

def verify_all_flattened():
    repos = os.listdir(REPOS_PATH)

    for repo in repos:
        repo_path = f"{REPOS_PATH}/{repo}"
        check_flattened_repo(repo_path)


if __name__ == "__main__":
    repos = os.listdir(REPOS_PATH)

    for repo in repos:
        if repo != "2024-12-bakerfi":
            continue

        repo_path = f"{REPOS_PATH}/{repo}"
        os.makedirs(f"{repo_path}/flattened", exist_ok=True)

        flatten_repo_path = f"{REPOS_PATH}/{repo}"
        try:
            flatten_repo(flatten_repo_path)
            all_flattened = check_flattened_repo(flatten_repo_path)
            print(f"All flattened: {all_flattened}")
            
            print(colored(f"Successfully flattened {repo}", "green"))
        except Exception as e:
            print(colored(f"Error flattening {repo}: {e}", "red"))