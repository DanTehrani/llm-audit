from slither.utils.output import Contract
from slither import Slither 
import os
from termcolor import colored

from utils import get_source_code_at

#REPO_PATH = "/Users/danieltehrani/dev/repos/2025-04-virtuals-protocol/flattened"
REPO_PATH = "/Users/danieltehrani/dev/repos/2025-08-gte-perps/flattened"
files_in_flatten_repo = os.listdir(REPO_PATH)

# Find a contract by name in a list of contracts
def find_contract_by_name(contracts: list[Contract], contract_name: str):
    for contract in contracts:
        if contract.name == contract_name:
            return contract

    return None

def remove_duplicates(contract_code: str):
    return "\n".join(set(contract_code.split("\n")))

def add_impl_for_contract(flatten_contract_path: str):
    print(f"\n\nAdding implementations for {flatten_contract_path}")
    print("--------------------------------")
    slither = Slither(flatten_contract_path, solc_args="--via-ir")

    with open(flatten_contract_path, "r") as f:
        contract_code = f.read()

    for contract in slither.contracts:
        if contract.name.startswith("I"):
            # This is a contract which the interface in the parent file refers to
            contract_name = contract.name[1:]
            print(f"\ncontract_name: {contract_name} interface name: {contract.name}")

            # Check if the interface exists in the slither contract list
            contract_exists_in_file = find_contract_by_name(slither.contracts, contract_name)

            # If the implementation already exists, we don't need to do anything
            if contract_exists_in_file:
                print(f"Contract {contract_name} already exists in the slither contract list")
                continue
            
            # Check if the implementation exists in the flattened repo
            contract_impl_exists = files_in_flatten_repo.count(f"{contract_name}.flattened.sol") > 0
           
            # If the implementation exists, we need to add it to the parent contract
            if contract_impl_exists:
                contract_impl_file_path = f"{REPO_PATH}/{contract_name}.flattened.sol"
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
                            print(f"Adding implementation {contract_name}:{impl_contract.name}")
                            contract_code = contract_code + "\n" + contract_impl_code
                        except Exception as e:
                            print(f"Error adding implementation {contract_name}:{impl_contract.name}: {e}")
                            continue
                    else:
                        print(f"Implementation {impl_contract.name} already exists in the slither contract list")
        else:
            print(f"Contract {contract.name} is not an interface")

    output_path = flatten_contract_path.replace("/flattened", "/flattened_with_impls").replace(".flattened.sol", ".with_impls.sol")

    with open(output_path, "w") as f:
        f.write(contract_code)

    """
    # Remove duplicates
    slither = Slither(output_path, solc_args="--via-ir")
    for contract in slither.contracts:
        duplicates = [c for c in slither.contracts if c.name == contract.name]
        if len(duplicates) > 1:
            print(f"Removing {len(duplicates) - 1} duplicates for {contract.name}")
            for duplicate in duplicates[1:]:
                duplicate_code = get_source_code_at(output_path, duplicate.source_mapping)
                contract_code = contract_code.replace(duplicate_code, "")

    with open(output_path, "w") as f:
        f.write(contract_code)
    """

if __name__ == "__main__":
    for file in files_in_flatten_repo:
        if file.endswith(".flattened.sol"):
            try:
                add_impl_for_contract(f"{REPO_PATH}/{file}")
            except Exception as e:
                print(f"Error adding implementations for {file}: {e}")
                continue