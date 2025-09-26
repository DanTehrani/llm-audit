from firebase_client import bucket
from utils import get_env
import json

env = get_env()

def view_eval_result():
    prefix = f"eval-runs-{env}/2025-02-thorwallet"          # folder you want to inspect

    eval_results = bucket.list_blobs(prefix=prefix)
    for eval_result in eval_results:
        print(eval_result.name)

if __name__ == "__main__":
    view_eval_result()