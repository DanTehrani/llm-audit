from langfuse import Langfuse
import os
import dotenv

dotenv.load_dotenv()

langfuse = Langfuse(
  secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
  public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
  host="https://us.cloud.langfuse.com"
)