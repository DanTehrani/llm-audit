from asyncore import file_dispatcher
from re import I
from slither.slither import Slither
from slither.utils.output import Contract
from slither.core.declarations.function_contract import FunctionContract
from openai_client import client
from utils import O3_MINI_PRICE_PER_1M_INPUT_TOKENS, O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS, ContractOverview, FilesToAudit, call_openai, get_solc_version, get_source_code_at, set_solc_version
from utils import FunctionAuditResult
import os
import json
from datetime import datetime
from termcolor import colored
import asyncio
import time
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio
import pickle
from langfuse import observe, get_client


model = "gpt-5-mini"

async def answer_question(question: str, contract_name: str, contract_path: str, past_questions_and_answers: str = "", call_metadata: dict = None):
    with open(contract_path, "r") as f:
        contract_code = f.read()

    prompt = f"""
    This is a question about the {contract_name} smart contract
    Answer the question. Only answer the question, do NOT suggest any improvements, fixes, or potential vulnerabilities.

    {question}

    These are the past questions and answers you have answered:
    {past_questions_and_answers}

    This is the smart contract code:
    {contract_code}
    
    """

    response = await call_openai(
            model=model,
            instructions="You are a smart contract security expert.",
            prompt=prompt,
            metadata=call_metadata,
        )

    answer = response.output_text

    return answer, response.usage
    

bad_descriptions = [
    "The  function X is public and does not impose any access restrictions, allowing any actor to call it. A malicious actor could exploit this by adding arbitrary addresses (including their own) to Y. This could corrupt Y and interfere with any subsequent operations or consensus mechanisms that rely on a trusted set of Y.",
    """
    Anyone can add their address to the Y.
    This may have cascading effects if other parts of the system rely on the Y.
    """
    """
    The function X is public and does not impose any access restrictions.
    This creates a potential vulnerability in the system if other parts of the system rely on the Y.
    """
]

good_descriptions = [
    "The function X can be called by anyone. And attacker can call the function X with their address to add their address into the state variable Z. Then they can call function Y which refers to Z to execute and distribute ETH.",
    """
    The function X is public and does not impose any access restrictions.
    A malicious actor could include their address in the state variable Z by calling the function X with their address.
    The function Y will then execute and distribute the fees to Z.
    """
]

def get_question_prompt(function_source_code: str, questions_and_answers: str, context: str):
    prompt = f"""
        You are a CONSERVATIVE vulnerability triager. You MUST NOT assume any behavior that is not directly evidenced by: 
        (a) the provided source code/AST/excerpts (with line numbers), or 
        (b) prior Q&A provided in this prompt.

        Rule 1 — Proof or Abstain:
        - Report an issue only if you can present a concrete exploit narrative that references exact functions, state vars, and code lines you have actually seen here.
        - If any link in the chain requires info you do not have, DO NOT infer it. Instead, output exactly one targeted Question to obtain the missing fact(s).

        Rule 2 — No Vague Language:
        - Do not use "could", "might", "potentially", "if", "assume", or similar hedging. State only what is true from evidence you cite.

        Rule 3 - Adversarial by Default:
        - An external address or contract passed in via constructor/initializer or setter can be trusted by default. Do NOT assume that it might be adversarial.

        Rule 4 — Only One Issue Per Question:
        - Think how one could maliciously call the contract to cause unintended behavior. Ask questions
        about the function and the contract to understand how one could maliciously call the function.

        You should identify is this function can be exploited by an malicious actor in the following context:
        {context}
    
        Here is the function to audit:
        {function_source_code}

        Ask a question about the function to understand it better.
        Ask the question in the following format:
        Question: <question>

        You have already asked the following questions and got the following answers. Don't ask the same questions again:
        {questions_and_answers}

        Ask questions to
        - Understand the expected behavior of the function
        - Understand the function in the context of the whole contract
        - Understand the state variables used in the function
        - Understand the implementation of functions that are called in the function
        - Understand the implementation of an external function called in the function
        - Understand the cascading effects of the function
        - Understand if an external contract can be trusted or not
        - Confirm the findings with the code

        You should describe the issue, with an end-to-end specific explanation of the vulnerability.
        Point out how exactly can the function be exploited by pointing out the exact function names, state variable names,
        variable names, and contract names that are related to the issue end-to-end. Do NOT use vague terms like 
        "any function that depends on the function" or "any state variable that depends on the function". Be specific.

        Good description:
        {chr(10).join(good_descriptions)}

        Bad descriptions:
        {chr(10).join(bad_descriptions)}

        Do NOT consider the followings as issues:
        - Lack of zero address input validation
        - Vulnerabilities as a result of private key exposure/account compromise
        - Admin account compromise
        - Missing event emission
        - Mistakes in the inputs of a function call
        - Not accounting for fee‐on‐transfer behavior
        - Address being maliciously set during the initialization of the contract
        """

    return prompt

def get_final_answer_prompt(function_source_code: str, questions_and_answers: str, context: str):
    prompt = f"""
    You are a CONSERVATIVE vulnerability triager. You MUST NOT assume any behavior that is not directly evidenced by: 
    (a) the provided source code/AST/excerpts (with line numbers), or 
    (b) prior Q&A provided in this prompt.

    Rule 1 — Proof or Abstain:
    - Report an issue only if you can present a concrete exploit narrative that references exact functions, state vars, and code lines you have actually seen here.

    Rule 2 — No Vague Language:
    - Do not use "could", "might", "potentially", "if", "assume", or similar hedging. State only what is true from evidence you cite.

    Rule 3 - Adversarial by Default:
    - An external address or contract passed in via constructor/initializer or setter can be trusted by default. Do NOT assume that it might be adversarial.

    You should identify is this function can be exploited by an malicious actor in the following context:
    {context}

    Here is the function to audit:
    {function_source_code}

    These are the questions and answers you have asked and got:
    {questions_and_answers}

    Given the questions and answers, if you have NOT found any issues, return a JSON object with the following fields:
    {{
        "safe": true,
        "reason": "Your reason for not finding any issues",
        "description": "Your description of the function's security"
    }}

    If you have identified an issue, you should describe the issue, with a specific explanation of the vulnerability.
    Also, provide a proposed fix in the "proposedFix" field.
    Return your assessment of the function's security in a JSON object with the following fields:
    {{
        "safe": false,
        "reason": string,
        "description": string,
        "proposedFix": string
    }}
    Only return the JSON object. Do not return any other text.

    Good description:
    {chr(10).join(good_descriptions)}

    Bad descriptions:
    {chr(10).join(bad_descriptions)}

    Do NOT consider the followings as issues:
    - Lack of zero address input validation
    - Vulnerabilities as a result of private key exposure/account compromise
    - Admin account compromise
    - Missing event emission
    - Mistakes in the inputs of a function call
    - Not accounting for fee‐on‐transfer behavior
    - Integer overflow/underflow/division by zero does not result in a denial of service attack if Solidity's built-in arithmetic checks are used
    - Do NOT assume that an admin role will act maliciously. Assume that an admin role will act in the best interest of the contract.
    """

    return prompt

def save_qa(contract_name: str, function_name: str, questions: list[str], answers: list[str]):
    os.makedirs(f"./qa/{contract_name}", exist_ok=True)

    qas = [{ "question": question, "answer": answer } for question, answer in zip(questions, answers)]
    with open(f"./qa/{contract_name}/{function_name}.json", "w") as f:
        json.dump(qas, f, indent=4, default=str)

langfuse = get_client()

@observe(capture_input=False, capture_output=False)
async def audit_function(contract_path: str, function: FunctionContract, contract: Contract, context: str):
    now = int(datetime.now().timestamp())
    langfuse.update_current_trace(session_id=f"{contract.name}-{function.name}-{now}")
    langfuse.update_current_span(
        metadata={"context": context}
    )

    questions: list[str] = []
    answers: list[str] = []
    
    max_questions = 5

    function_source_code = get_source_code_at(contract_path, function.source_mapping)
    contract_source_code = get_source_code_at(contract_path, contract.source_mapping)

    total_questions_input_tokens_usage = 0
    total_questions_output_tokens_usage = 0
    total_answers_input_tokens_usage = 0
    total_answers_output_tokens_usage = 0

    for i in range(max_questions):
        print(f"Auditing function {function.name} {i}/{max_questions}")
        questions_and_answers = "\n".join([f"Question: {question}\nAnswer: {answer}" for question, answer in zip(questions, answers)])
        
        prompt = get_question_prompt(function_source_code, questions_and_answers, context, contract_source_code)

        call_metadata = {
            "question_index": i,
            "function_name": function.name,
            "contract_name": contract.name,
            "context": context,
        }

        start = time.time()
        response = await call_openai(
            model=model,
            instructions="You are a smart contract security expert.",
            prompt=prompt,
            metadata=call_metadata,
        )
        end = time.time()
        print(colored(f"Question time: {end - start} seconds", "blue"))

        total_questions_input_tokens_usage += response.usage.input_tokens
        total_questions_output_tokens_usage += response.usage.output_tokens

        question = response.output_text.split("Question:")[1].strip()

        start = time.time()
        answer, qa_usage = await answer_question(question, contract.name, contract_path,  questions_and_answers, call_metadata)
        end = time.time()
        print(colored(f"Answer time: {end - start} seconds", "blue"))

        total_answers_input_tokens_usage += qa_usage.input_tokens
        total_answers_output_tokens_usage += qa_usage.output_tokens

        answers.append(answer)
        questions.append(question)

        save_qa(contract.name, function.name, questions, answers)

    prompt = get_final_answer_prompt(function_source_code, questions_and_answers, context)

    response = await call_openai(
        model=model,
        instructions="You are a smart contract security expert.",
        prompt=prompt,
    )

    total_input_tokens_usage = total_questions_input_tokens_usage + total_answers_input_tokens_usage
    total_output_tokens_usage = total_questions_output_tokens_usage + total_answers_output_tokens_usage

    input_tokens_cost = total_input_tokens_usage * O3_MINI_PRICE_PER_1M_INPUT_TOKENS / 1_000_000
    output_tokens_cost = total_output_tokens_usage * O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000

    final_answer = response.output_text
    final_answer_parsed = json.loads(final_answer.replace("```json", "").replace("```", ""))

    result = FunctionAuditResult(
        function_name=function.name,
        safe=final_answer_parsed["safe"],
        reason=final_answer_parsed["reason"],
        description=final_answer_parsed["description"],
        cost=f"{total_input_tokens_usage} input tokens, {total_output_tokens_usage} output tokens, ${input_tokens_cost:.6f} input cost, ${output_tokens_cost:.6f} output cost",
        proposedFix=final_answer_parsed["proposedFix"] if "proposedFix" in final_answer_parsed else None,
        failed=False
    )

    return result

async def try_audit_function(contract_path: str, function: FunctionContract, contract: Contract, context: str):
    try:
        return await audit_function(contract_path, function, contract, context)
    except Exception as e:
        print(colored(f"Error auditing function {function.name}: {e}", "red"))
        return FunctionAuditResult(
            function_name=function.name,
            safe=False,
            reason=str(e),
            description="",
            cost="",
            proposedFix=None,
            failed=True
        )

CONTRACT_OVERVIEW_DIR = "./contract_overviews"

async def get_contract_overview(contract_path: str, entry_point_contract: Contract):
    os.makedirs(CONTRACT_OVERVIEW_DIR, exist_ok=True)

    # Try to load the contract overview from file
    contract_overview_file = f"{CONTRACT_OVERVIEW_DIR}/{entry_point_contract.name}.pkl"
    if os.path.exists(contract_overview_file):
        with open(contract_overview_file, "rb") as f:
            return pickle.load(f)

    # Contract overview doesn't exist yet, so we need to get it
    with open(contract_path, "r") as f:
        full_contract_code = f.read()

    print("Getting contract overview for", entry_point_contract.name)

    response = await call_openai(
        model=model,
        instructions="You are an assistant that summarizes and explains a smart contract.",
        prompt=f"""
        Give a high level overview of the contract please.
        Please include the followings
        - Purpose of the contract
        - Roles & authorities: owner, admin, governor, upgrader, pauser, minter, etc.
        - Trusted parties/components: oracles, relayers, external protocols, multisigs, timelocks, etc.
        - Value flows: who can move which assets, under what conditions.
        - Mechanisms: How parts of the contract works. (list all of the mechanisms)
        - Invariants: Expected state of the contract, or expected behavior of the contract.

        The entrypoint contract is:
        {entry_point_contract.name}

        Here is the full contract code:
        {full_contract_code}

        Return in a JSON object with the following fields:
        {{ 
            "purpose": "string",
            "roles": ["string"],
            "trusted_parties": ["string"],
            "value_flows": ["string"],
            "mechanisms": ["string"],
            "invariants": ["string"]
        }}
        Only return the JSON object. Do not return any other text.
        """,
    )

    output = json.loads(response.output_text.replace("```json", "").replace("```", ""))

    contract_overview = ContractOverview(**output)

    # Save the contract overview to file
    with open(contract_overview_file, "wb") as f:
        pickle.dump(contract_overview, f)

    return contract_overview

AUDIT_FUNCTIONS = [
    "claimTitn",
]

def get_entry_point_functions(contract: Contract):
    return [f for f in contract.functions_entry_points if (f.contract_declarer.name == contract.name and not f.view)]

async def audit_contract(contract_path: str, contract: Contract, project_name: str):
    if contract.name != "MergeTgt":
        return

    entry_point_functions = get_entry_point_functions(contract)
    entry_point_functions = [f for f in entry_point_functions if f.name in AUDIT_FUNCTIONS]

    start_get_contract_overview = time.time()
    contract_overview = await get_contract_overview(contract_path, contract)
    end_get_contract_overview = time.time()
    print(colored(f"Getting contract overview took {end_get_contract_overview - start_get_contract_overview} seconds", "blue"))

    print(f"{len(contract_overview['mechanisms'])} mechanisms identified")
    
    audit_function_tasks = []
    for function in entry_point_functions:
        for value_flow_context in zip(["General context"] + contract_overview["mechanisms"]):
        #for value_flow_context in  ["General context"]:
            audit_function_tasks.append(try_audit_function(contract_path, function, contract, value_flow_context))

    results: list[FunctionAuditResult] = await tqdm_asyncio.gather(*audit_function_tasks, desc=f"Auditing {contract.name}", colour="green")

    results_unique_functions = []
    for entry_point_function in entry_point_functions:
        function_results = [result for result in results if result["function_name"] == entry_point_function.name]
        unsafe_function_results = [result for result in function_results if not result["safe"]]
        if len(unsafe_function_results) > 0:
            results_unique_functions.append(unsafe_function_results[0])
    
    # Save audit results to file
    audit_result_dir = f"./audits/{project_name}/{contract.name}"
    os.makedirs(audit_result_dir, exist_ok=True)

    now = int(datetime.now().timestamp())

    with open(f"{audit_result_dir}/result-{now}.json", "w") as f:
        json.dump(results_unique_functions, f, indent=4, default=str)


def get_entry_point_contract(contract_path: str, project_name: str):
    contract_name = contract_path.split("/")[-1].replace(".with_impls.sol", "")
    solc_version = get_solc_version(project_name);

    if solc_version is None:
        raise Exception(f"Solc version not found for {project_name}")

    set_solc_version(solc_version)

    if solc_version != "0.8.0":
        slither = Slither(contract_path, solc_args="--via-ir")
    else:
        slither = Slither(contract_path)

    for contract in slither.contracts:
        if contract.name == contract_name:
            return contract

    return None

#DIR_PATH = "/Users/danieltehrani/dev/repos/2025-04-virtuals-protocol/flattened_with_impls"
#DIR_PATH = "/Users/danieltehrani/dev/repos/2025-08-gte-perps/flattened_with_impls"

async def audit_flattened_contract_file(project_path: str, file_path: str, project_name: str):
    contract_path = os.path.join(project_path, file_path)
    entry_point_contract = get_entry_point_contract(contract_path, project_name)

    if entry_point_contract is None:
        raise Exception(f"No entry point contract found for {contract_path}")

    try:
        await audit_contract(contract_path, entry_point_contract, project_name)
    except Exception as e:
        print(colored(f"Error auditing {contract_path}: {e}", "red"))
        print(e)


async def eval_project(project_path: str, files_to_audit: list[str], project_name: str):
    audit_function_tasks = []
    for file in files_to_audit:
        audit_function_tasks.append(audit_flattened_contract_file(project_path, file, project_name))

    await tqdm_asyncio.gather(*audit_function_tasks, desc=f"Auditing {project_name}", colour="green")

if __name__ == "__main__":
    files_to_audit: list[FilesToAudit] = json.load(open("./files_to_audit.json", "r"))

    eval_project_tasks = [] 
    for project in files_to_audit:
        project_name = project["project"]

        if project_name != "2025-02-thorwallet":
            continue

        eval_project_tasks.append(eval_project(f"/Users/danieltehrani/dev/repos/{project_name}/flattened_with_impls", project["files"], project_name))

    start_time = time.time()
    asyncio.run(tqdm_asyncio.gather(*eval_project_tasks, desc="Auditing all projects", colour="green"))
    end_time = time.time()
    print(colored(f"Auditing all projects took {end_time - start_time} seconds", "green"))

