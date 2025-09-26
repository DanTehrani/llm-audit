import json
import string
from openai.types.responses import Response, ResponseUsage
from slither.core.slither_core import Source, Contract
from typing import TypedDict
from termcolor import colored
import os
import subprocess
import asyncio
import time
import backoff
import httpx
from openai import AsyncOpenAI
# Import the SDK's exception types (new SDK)
from openai import (
    APIError, APIStatusError, APITimeoutError, APIConnectionError, RateLimitError
)
from lib.openai_client import client

class FunctionAuditResult(TypedDict):
    project_name: str
    function_name: str
    safe: bool
    reason: str
    description: str
    cost: str
    proposedFix: str | None
    failed: bool

class TargetFinding(TypedDict):
    title: str
    description: str

class ProjectToAudit(TypedDict):
    project: str
    files: list[str]


class TargetFindingWithSeverity(TypedDict):
    id: int
    title: str
    description: str
    severity: str

class ContractOverview(TypedDict):
    purpose: str
    roles: list[str]
    trusted_parties: list[str]
    value_flows: list[str]
    invariants: list[str]

class JudgeResult(TypedDict):
    project_name: str
    target_finding: TargetFindingWithSeverity
    llm_finding: FunctionAuditResult | None
    is_true_positive: bool
    failed: bool

class EvalResult(TypedDict):
    function_name: str
    true_negatives: list[TargetFindingWithSeverity]
    false_positives: list[FunctionAuditResult]
    true_positives: list[tuple[TargetFindingWithSeverity, FunctionAuditResult]]
    false_positive_rate: float
    true_positive_rate: float

GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS = 10
GPT_4O_PRICE_PER_1M_INPUT_TOKENS = 2.5

O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS = 4.40
O3_MINI_PRICE_PER_1M_INPUT_TOKENS = 1.1

GPT_5_PRICE_PER_1M_OUTPUT_TOKENS = 10
GPT_5_PRICE_PER_1M_INPUT_TOKENS = 1.25

GPT_5_NANO_PRICE_PER_1M_OUTPUT_TOKENS = 0.40
GPT_5_NANO_PRICE_PER_1M_INPUT_TOKENS = 0.05

GPT5_MINI_PRICE_PER_1M_OUTPUT_TOKENS = 2
GPT5_MINI_PRICE_PER_1M_INPUT_TOKENS = 0.25

REPOS_PATH = "./dataset"

PROJECT_CONFIGS = [
    {
        "name": "2025-02-thorwallet",
        "solc": "0.8.27"
    },
    {
        "name": "2025-02-thorwalletr",
        "solc": "0.8.30"
    },
    {
        "name": "2025-08-gte-perps",
        "solc": "0.8.27"
    },
    {
        "name": "2025-03-nudgexyz",
        "solc": "0.8.28"
    },
    {
        "name": "2025-04-virtuals-protocol",
        "solc": "0.8.20"
    },
    {
        "name": "2025-04-bitvault",
        "solc": "0.8.30"
    },
    {
        "name": "2025-05-upside",
        "solc": "0.8.24"
    },
    {
        "name": "2025-04-kinetiq",
        "solc": "0.8.30"
    },
    {
        "name": "2025-04-forte",
        "solc": "0.8.30"
    }
]

UNSUPPORTED_PROJECTS = [
    "2025-08-gte-perps",
    "2025-06-panoptic", 
    "2025-04-kinetiq", 
    "2025-04-virtuals-protocol", 
    "2025-01-iq-ai", 
    "2025-05-blackhole", 
    "2025-03-silo-finance", 
    "2025-01-next-generation", 
    "2025-08-morpheus"
    ]

def get_solc_version(project_name: str):
    for project in PROJECT_CONFIGS:
        if project["name"] == project_name:
            return project["solc"]
    return "0.8.30"

def set_solc_version(solc_version: str):
    result = subprocess.run(
            f"solc-select use {solc_version}",
            capture_output=True,   # capture stdout/stderr
            shell=True,
            text=True              # decode bytes → str
        )

    if result.returncode != 0:
        raise ValueError(f"Failed to set solc version: {result.stderr}")
        
    return result.stdout

def get_projects():
    repos = os.listdir(REPOS_PATH)

    return [repo for repo in repos if repo not in UNSUPPORTED_PROJECTS]

def get_files_in_scope(repo_full_dir_path: str):
    with open(f"{repo_full_dir_path}/scope.txt", "r") as f:
        scopes_file = f.read()
    
    scopes = scopes_file.split("\n")
    return [scope.strip() for scope in scopes if ".sol" in scope.strip()]


def print_cost(response: ResponseUsage, model: str): 
    if model == "gpt-4o":
        input_tokens_price = GPT_4O_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    elif model == "o3-mini":
        input_tokens_price = O3_MINI_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    elif model == "gpt-5":
        input_tokens_price = GPT_5_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = GPT_5_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    elif model == "gpt-5-nano":
        input_tokens_price = GPT_5_NANO_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = GPT_5_NANO_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
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


def get_env():
    is_rendered = os.environ.get("RENDER")
    if is_rendered:
        return "prod"

    else:
        return "dev"

def get_latest_audit_results():
    latest_audit_results = os.listdir(f"./audits/")
    latest_audit_timestamp = 0  

    for latest_audit_result in latest_audit_results:
        try:
            audit_timestamp = int(latest_audit_result.split("-")[-1].split(".")[0])
            latest_audit_timestamp = max(latest_audit_timestamp, audit_timestamp)
        except:
            print(colored(f"Error parsing audit timestamp for {latest_audit_result}", "red"))
            continue

    with open(f"./audits/audit-{latest_audit_timestamp}.json", "r") as f:
        audit_results: list[FunctionAuditResult] = json.load(f)

    return audit_results


OPENAI_CONCURRENCY = 5
openai_sem = asyncio.BoundedSemaphore(OPENAI_CONCURRENCY)

def _give_up(e: Exception) -> bool:
    # Give up on non-retryable 4xx (except 429)
    if isinstance(e, APIStatusError):
        return (400 <= e.status_code < 500) and (e.status_code != 429)
    return False

@backoff.on_exception(
    backoff.expo,  # exponential backoff with jitter
    (
        # OpenAI SDK exceptions
        APIError, APIStatusError, APITimeoutError, APIConnectionError, RateLimitError,
        # httpx lower-level exceptions (sometimes bubble up)
        httpx.TimeoutException, httpx.HTTPError,
    ),
    max_tries=5,
    giveup=_give_up,
)
async def call_openai(model: str, instructions: str, prompt: str, metadata: dict = None):
    async with openai_sem:
        return await client.responses.create(
            model=model,
            instructions=instructions,
            input=prompt,
            service_tier="priority",
            metadata=metadata,
        )