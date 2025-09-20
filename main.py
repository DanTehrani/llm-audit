from slither.core.cfg.node import StateVariable
from slither.core.expressions import CallExpression
from slither.core.slither_core import Source
from slither.slither import Slither
from slither.utils.output import Contract
from slither.core.declarations.function_contract import FunctionContract
from openai_client import client
from utils import print_cost, get_source_code_at

# Get function by name from Slither's Contract object
def get_function_by_name(contract: Contract, name: str):
    found = [func for func in contract.functions if func.name == name]
    if len(found) == 0:
        return None

    return found[0]

# Get modifier by name from Slither's Contract object
def get_modifier_by_name(contract: Contract, name: str):
    found = [modifier for modifier in contract.modifiers if modifier.name == name]
    if len(found) == 0:
        return None

    return found[0]

def audit_function(contract_path: str, function: FunctionContract, contract: Contract):
    print(f"Auditing function: {function.name}")

    # Get all function source code that use the same state variables as the current function
    functions_using_same_state_vars: list[str] = []
    for state_var in function.state_variables_written:
        for function_i in contract.functions:
            if state_var in function_i.state_variables_read or state_var in function_i.state_variables_written:
                if (function.id != function_i.id):
                    function_source = get_source_code_at(contract_path, function_i.source_mapping)
                    functions_using_same_state_vars.append(function_source)


    # All functions that the current function refers to
    function_references = []
    for expression in function.all_expressions():
        if type(expression) == CallExpression:
            function_name = get_source_code_at(contract_path, expression._called.source_mapping)

            referred_function = get_function_by_name(contract, function_name)
            referred_modifier = get_modifier_by_name(contract, function_name)

            if referred_modifier:
                function_references.append(get_source_code_at(contract_path, referred_modifier.source_mapping))
            elif referred_function:
                function_references.append(get_source_code_at(contract_path, referred_function.source_mapping))

   
    function_source_code = get_source_code_at(contract_path, function.source_mapping)

    prompt = f"""
    This is a function of a smart contract.

    Do you see any potential security issues in this function?

    Here is the function:
    {function_source_code}

    Here are the functions that the above function refers to:
    {chr(10).join(function_references)}

    Here are other functions that use the same state variables, hence might be affected by the implementation of the above function:
    {chr(10).join(functions_using_same_state_vars)}


    Return a JSON object with the following fields:
    - safe: boolean
    - reason: string
    - description: string

    Do NOT consider the followings as issues:
    - Lack of zero address input validation
    - Vulnerabilities as a result of private key exposure/account compromise
    - Admin account compromise
    - Missing event emission
    - Mistakes in the inputs of a function call
    """

    model = "o3-mini"
    response = client.responses.create(
        model=model,
        instructions="You are a smart contract security expert.",
        input=prompt,
    )

    print_cost(response, model)
    print(response.output_text)


contract_path = "./contracts/EtherBank.sol"
slither = Slither(contract_path)
contract = slither.contracts[0]

print(f"Auditing contract: {contract.name}")
for function in contract.functions_entry_points:
    audit_function(contract_path, function, contract)

