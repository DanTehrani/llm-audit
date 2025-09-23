from re import I
from slither.slither import Slither
from slither.utils.output import Contract
from slither.core.declarations.function_contract import FunctionContract
from openai_client import client
from utils import O3_MINI_PRICE_PER_1M_INPUT_TOKENS, O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS, print_cost, get_source_code_at
from utils import FunctionAuditResult
import os
import json
from datetime import datetime
from termcolor import colored
import asyncio

async def answer_question(question: str, contract_name: str, contract_path: str, past_questions_and_answers: str = ""):
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

    model = "o3-mini"
    response = await asyncio.to_thread(
            client.responses.create,
            model=model,
            instructions="You are a smart contract security expert.",
            input=prompt,
        )

    answer = response.output_text

    return answer, response.usage
    

bad_descriptions = [
    "The  function X is public and does not impose any access restrictions, allowing any actor to call it. A malicious actor could exploit this by adding arbitrary addresses (including their own) to Y. This could corrupt Y and interfere with any subsequent operations or consensus mechanisms that rely on a trusted set of Y.",
    """
    Anyone can add their address to the Y.
    This may have cascading effects if other parts of the system rely on the Y.
    """
]

good_descriptions = [
    "The function X can be called by anyone. And attacker can call the function X with their address to add their address into the state variable Z. Then they can call function Y which refers to Z to execute and distribute ETH.",
]

def get_question_prompt(function_source_code: str, questions_and_answers: str):
    prompt = f"""
        This is a function of a smart contract.
        You should identify is this function can be exploited by an malicious actor.
        Here is the function:
        {function_source_code}

        If you haven't found any issues that you are sure about, ask a question about the function to understand it better.
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

        If you have identified an issue, return the issue in a JSON object with the following fields:
        - safe: boolean
        - reason: string
        - description: string

        You should describe the issue, with a specific explanation of the vulnerability.

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

def get_final_answer_prompt(function_source_code: str, questions_and_answers: str):
    prompt = f"""
    This is a function of a smart contract.
    You should identify is this function can be exploited by an malicious actor.
    Here is the function:
    {function_source_code}

    These are the questions and answers you have asked and got:
    {questions_and_answers}

    Give the questions and answers, if you have NOT found any issues, return a JSON object with the following fields:
    - safe: true,
    - reason: "Your reason for not finding any issues",
    - description: "Your description of the function's security"

    If you have identified an issue, you should describe the issue, with a specific explanation of the vulnerability.
    Return your assessment of the function's security in a JSON object with the following fields:
    - safe: false
    - reason: string
    - description: string

    Follow the followings as a guide.

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
    """

    return prompt

def save_qa(contract_name: str, function_name: str, questions: list[str], answers: list[str]):
    print(colored(f"Saving QA for {contract_name}:{function_name}", "green"))
    print(f"Questions: {len(questions)}")
    print(f"Answers: {len(answers)}")
    os.makedirs(f"./qa/{contract_name}", exist_ok=True)

    qas = [{ "question": question, "answer": answer } for question, answer in zip(questions, answers)]
    with open(f"./qa/{contract_name}/{function_name}.json", "w") as f:
        json.dump(qas, f, indent=4, default=str)


async def audit_function(contract_path: str, function: FunctionContract, contract: Contract):
    print(f"Auditing function: {function.contract_declarer.name}:{function.name}")
    questions: list[str] = []
    answers: list[str] = []
    
    max_questions = 10

    function_source_code = get_source_code_at(contract_path, function.source_mapping)

    total_questions_input_tokens_usage = 0
    total_questions_output_tokens_usage = 0
    total_answers_input_tokens_usage = 0
    total_answers_output_tokens_usage = 0

    while True:
        questions_and_answers = "\n".join([f"Question: {question}\nAnswer: {answer}" for question, answer in zip(questions, answers)])

        if len(questions) < max_questions:
            prompt = get_question_prompt(function_source_code, questions_and_answers)
        else:
            prompt = get_final_answer_prompt(function_source_code, questions_and_answers)

        model = "o3-mini"
        response = await asyncio.to_thread(
            client.responses.create,
            model=model,
            instructions="You are a smart contract security expert.",
            input=prompt,
        )
        total_questions_input_tokens_usage += response.usage.input_tokens
        total_questions_output_tokens_usage += response.usage.output_tokens

        if "Question:" in response.output_text:
            print("\n")
            print(response.output_text)
            question = response.output_text.split("Question:")[1].strip()
            answer, qa_usage = await answer_question(question, contract.name, contract_path,  questions_and_answers)
            print("\nAnswer:")
            print(answer)
            print("\n Answer cost:")
            print_cost(qa_usage, model)
            print("\n")

            total_answers_input_tokens_usage += qa_usage.input_tokens
            total_answers_output_tokens_usage += qa_usage.output_tokens

            answers.append(answer)
            questions.append(question)

            save_qa(contract.name, function.name, questions, answers)
        else:
            final_answer = response.output_text
            break


        # Safety guard
        if len(questions) > max_questions:
            print("Max questions reached")
            final_answer = {
                "safe": True,
                "reason": "Max questions reached",
                "description": "Max questions reached"
            }
            break

    print(f"Total questions input tokens usage: {total_questions_input_tokens_usage}")
    print(f"Total questions output tokens usage: {total_questions_output_tokens_usage}")
    print(f"Total answers input tokens usage: {total_answers_input_tokens_usage}")
    print(f"Total answers output tokens usage: {total_answers_output_tokens_usage}\n\n")

    total_input_tokens_usage = total_questions_input_tokens_usage + total_answers_input_tokens_usage
    total_output_tokens_usage = total_questions_output_tokens_usage + total_answers_output_tokens_usage

    input_tokens_cost = total_input_tokens_usage * O3_MINI_PRICE_PER_1M_INPUT_TOKENS / 1_000_000
    output_tokens_cost = total_output_tokens_usage * O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000

    print(colored(f"Final answer: {final_answer}", "green"))

    final_answer_parsed = json.loads(final_answer.replace("```json", "").replace("```", ""))

    result = FunctionAuditResult(
        function_name=function.name,
        safe=final_answer_parsed["safe"],
        reason=final_answer_parsed["reason"],
        description=final_answer_parsed["description"],
        cost=f"{total_input_tokens_usage} input tokens, {total_output_tokens_usage} output tokens, ${input_tokens_cost:.6f} input cost, ${output_tokens_cost:.6f} output cost"
    )

    return result

AUDIT_FUNCTIONS = [
    "delegate",
]

async def audit_contract(contract_path: str, contract: Contract):
    print(colored(f"Auditing contract: {contract.name}", "green"))

    #entry_point_functions = [f for f in contract.functions_entry_points if f.contract_declarer.name == contract.name]
    entry_point_functions = [f for f in contract.functions_entry_points if f.name in AUDIT_FUNCTIONS]

    if len(entry_point_functions) > 30:
        print(colored(f"Skipping contract: {contract.name} with {len(entry_point_functions)} functions", "blue"))
        return

    print(colored(f"Auditing {len(entry_point_functions)} functions", "green"))

    results: list[FunctionAuditResult] = []

    sem = asyncio.Semaphore(5)  # limit to 5 concurrent tasks

    async def bounded_audit(function):
        async with sem:
            try:
                result = await audit_function(contract_path, function, contract)
                print(result)
                results.append(result)
            except Exception as e:
                print(colored(f"Error auditing function {function.name}: {e}", "red"))
                print(e)


    tasks = [asyncio.create_task(bounded_audit(fn)) for fn in entry_point_functions]
    await asyncio.gather(*tasks)

    # Save audit results to file
    audit_result_dir = f"./audits/contracts/{contract.name}"
    os.makedirs(audit_result_dir, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    with open(f"{audit_result_dir}/result-{today}.json", "w") as f:
        json.dump(results, f, indent=4, default=str)


def get_entry_point_contract(contract_path: str):
    contract_name = contract_path.split("/")[-1].replace(".with_impls.sol", "")

    slither = Slither(contract_path, solc_args="--via-ir")

    for contract in slither.contracts:
        if contract.name == contract_name:
            return contract

    return None

DIR_PATH = "/Users/danieltehrani/dev/repos/2025-04-virtuals-protocol/flattened_with_impls"

async def audit_flattened_contract_file(file_path: str):
    contract_path = os.path.join(DIR_PATH, file_path)
    entry_point_contract = get_entry_point_contract(contract_path)

    if entry_point_contract is None:
        print(f"No entry point contract found for {contract_path}")
        return

    await audit_contract(contract_path, entry_point_contract)

"""
files = os.listdir(DIR_PATH)
for file in files:
    try:
        audit_flattened_contract_file(file)
    except Exception as e:
        print(f"Error auditing {file}: {e}")
"""

asyncio.run(audit_flattened_contract_file("AgentVeToken.with_impls.sol"))