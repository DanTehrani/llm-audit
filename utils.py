from openai.types.responses import Response
from slither.core.slither_core import Source

GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS = 10;
GPT_4O_PRICE_PER_1M_INPUT_TOKENS = 2.5;

O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS = 1.1
O3_MINI_PRICE_PER_1M_INPUT_TOKENS = 4.40


def print_cost(response: Response, model: str): 
    if model == "gpt-4o":
        input_tokens_price = GPT_4O_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = GPT_4O_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    elif model == "o3-mini":
        input_tokens_price = O3_MINI_PRICE_PER_1M_INPUT_TOKENS / 1_000_000;
        output_tokens_price = O3_MINI_PRICE_PER_1M_OUTPUT_TOKENS / 1_000_000;
    else:
        raise ValueError(f"UNSUPPORTED model: {model}")

    input_tokens_cost = response.usage.input_tokens * input_tokens_price;
    output_tokens_cost = response.usage.output_tokens * output_tokens_price;

    cost_dollars = input_tokens_cost + output_tokens_cost;
    print(f"Tokens cost: ${cost_dollars:.6f} (input: ${input_tokens_cost:.6f}, output: ${output_tokens_cost:.6f})") 

def get_source_code_at(contract_file: str, source_mapping: Source):
    with open(contract_file, "r") as file:
        source_code = file.read()
        return source_code[source_mapping.start:source_mapping.end]

