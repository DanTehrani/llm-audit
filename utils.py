from openai.types.responses import Response, ResponseUsage
from slither.core.slither_core import Source
from typing import TypedDict
from termcolor import colored

class FunctionAuditResult(TypedDict):
    function_name: str
    safe: bool
    reason: str
    description: str
    cost: str

class TargetFinding(TypedDict):
    id: int
    title: str
    description: str

class ContractOverview(TypedDict):
    purpose: str
    roles: list[str]
    trusted_parties: list[str]
    value_flows: list[str]
    invariants: list[str]

GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS = 10;
GPT_4O_PRICE_PER_1M_INPUT_TOKENS = 2.5;

O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS = 1.1
O3_MINI_PRICE_PER_1M_INPUT_TOKENS = 4.40


def print_cost(response: ResponseUsage, model: str): 
    if model == "gpt-4o":
        input_tokens_price = GPT_4O_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    elif model == "o3-mini":
        input_tokens_price = O3_MINI_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    else:
        raise ValueError(f"UNSUPPORTED model: {model}")

    input_tokens = response.input_tokens
    output_tokens = response.output_tokens
    input_tokens_cost = input_tokens * input_tokens_price;
    output_tokens_cost = output_tokens * output_tokens_price;

    cost_dollars = input_tokens_cost + output_tokens_cost;
    print(colored(f"Tokens cost: ${cost_dollars:.6f} (input: {input_tokens} tokens, ${input_tokens_cost:.6f}, output: {output_tokens} tokens, ${output_tokens_cost:.6f})", "blue")) 

def get_source_code_at(contract_file: str, source_mapping: Source):
    # source_mapping must have .start and .length (not .end)
    start = source_mapping.start
    length = source_mapping.length  # NOT an end index

    with open(contract_file, "rb") as f:              # read raw bytes
        data = f.read()

    snippet_bytes = data[start:start + length]         # byte-accurate slice
    return snippet_bytes.decode("utf-8", errors="strict")