from slither.utils.output import Contract
from slither import Slither 
import os
from termcolor import colored
from utils import get_files_in_scope, get_projects, get_source_code_at

# Find a contract by name in a list of contracts
def find_contract_by_name(contracts: list[Contract], contract_name: str):
    for contract in contracts:
        if contract.name == contract_name:
            return contract

    return None

def add_impl_for_contract(flatten_contract_path: str, files_in_flatten_repo: list[str], repo_path: str):
    print(f"\n\nAdding implementations for {flatten_contract_path}")
    print("--------------------------------")
    slither = Slither(flatten_contract_path, solc_args="--via-ir")

    with open(flatten_contract_path, "r") as f:
        contract_code = f.read()

    for contract in slither.contracts:
        if contract.name.startswith("I"):
            # This is a contract which the interface in the parent file refers to
            contract_name = contract.name[1:]

            # Check if the interface exists in the slither contract list
            contract_exists_in_file = find_contract_by_name(slither.contracts, contract_name)

            # If the implementation already exists, we don't need to do anything
            if contract_exists_in_file:
                continue
            
            # Check if the implementation exists in the flattened repo
            contract_impl_exists = files_in_flatten_repo.count(f"{contract_name}.flattened.sol") > 0
           
            # If the implementation exists, we need to add it to the parent contract
            if contract_impl_exists:
                contract_impl_file_path = f"{repo_path}/{contract_name}.flattened.sol"
                # Load the Slither instance of the file that has the implementation
                slither_contract_impl = Slither(contract_impl_file_path, solc_args="--via-ir")

                # For each implementation, add it to the parent contract if it doesn't already exist
                for impl_contract in slither_contract_impl.contracts:
                    # Check if the implementation already exists in the slither contract list
                    already_exists = find_contract_by_name(slither.contracts, impl_contract.name)

                    if not already_exists:
                        # Add the implementation to the parent contract
                        try:
                            contract_impl_code = get_source_code_at(contract_impl_file_path, impl_contract.source_mapping)
                            contract_code = contract_code + "\n" + contract_impl_code
                        except Exception as e:
                            print(colored(f"Error adding implementation {contract_name}:{impl_contract.name}: {e}", "red"))
                            continue

    output_path = flatten_contract_path.replace("/flattened", "/flattened_with_impls").replace(".flattened.sol", ".with_impls.sol")

    with open(output_path, "w") as f:
        f.write(contract_code)


def add_impls_for_repo(flatten_repo_path: str):
    files_in_flatten_repo = os.listdir(flatten_repo_path)

    for file in files_in_flatten_repo:

        #if file != "FundingRateEngine.flattened.sol":
         #   continue
        
        if file.endswith(".flattened.sol"):
            try:
                add_impl_for_contract(f"{flatten_repo_path}/{file}", files_in_flatten_repo, flatten_repo_path)
            except Exception as e:
                print(colored(f"Error adding implementations for {file}: {e}", "red"))
                continue

def check_added_impls(repo_full_dir_path: str):
    files_in_flatten_repo = os.listdir(f"{repo_full_dir_path}/flattened_with_impls")
    files_in_scope = get_files_in_scope(repo_full_dir_path)

    missing_files = []
    for file in files_in_scope:
        expected_file_name = file.split("/")[-1].replace(".sol", ".with_impls.sol")

        if expected_file_name not in files_in_flatten_repo:
            #print(colored(f"File {file} not found in {repo_full_dir_path}/flattened_with_impls", "red"))
            missing_files.append(file)

    if len(missing_files) > 0:
        return False

    return True

REPOS_PATH = "/Users/danieltehrani/dev/repos"

if __name__ == "__main__":
    repos = get_projects()
    for repo in repos:
        repo_path = f"{REPOS_PATH}/{repo}"
        os.makedirs(f"{repo_path}/flattened_with_impls", exist_ok=True)
        flatten_repo_path = f"{REPOS_PATH}/{repo}/flattened"

        all_added = check_added_impls(repo_path)
        print(colored(f"All implementations added: {all_added} {repo}", "green"))

        if all_added:   
            # Skip if all implementations are already added
            continue

        try:
            #add_impls_for_repo(flatten_repo_path)
            print(colored(f"Successfully added implementations for {repo}", "green"))
        except Exception as e:
            print(colored(f"Error adding implementations for {repo}: {e}", "red"))
            continue