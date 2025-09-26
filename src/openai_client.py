import os
import dotenv
#from openai import AsyncOpenAI
from langfuse.openai import AsyncOpenAI
import httpx
import asyncio

# One client, one warm connection pool, HTTP/2 on.
http = httpx.AsyncClient(
    http2=True,
    timeout=httpx.Timeout(60.0, connect=10.0),
    limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
)

dotenv.load_dotenv()

client = AsyncOpenAI(
        #http_client=http,
        timeout=120,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

if __name__ == "__main__":
    response = asyncio.run(client.responses.create(
        model="gpt-4o",
        instructions="You are a coding assistant that talks like a pirate.",
        input="How do I check if a Python object is an instance of a class?",
        service_tier="priority"
    ))

    print(response.output_text)