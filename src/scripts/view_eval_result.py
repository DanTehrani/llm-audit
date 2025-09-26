from lib.firebase_client import bucket
from utils import get_env
import json
from termcolor import colored


#env = get_env()
env = "prod"

def view_eval_result():
    prefix = f"eval-runs-{env}/judge_results"          # folder you want to inspect

    eval_results = bucket.list_blobs(prefix=prefix)
    latest_audit_timestamp = 0
    for eval_result in eval_results:
        try:
            audit_timestamp = eval_result.name.split("-")[-1].split(".")[0]
            latest_audit_timestamp = max(latest_audit_timestamp, int(audit_timestamp))
        except:
            print(colored(f"Error parsing audit timestamp for {eval_result.name}", "red"))   
            continue

    print(latest_audit_timestamp)
    blob = bucket.blob(f"{prefix}/judge-{latest_audit_timestamp}.json")
    json_text = blob.download_as_text()

    latest_audit_results = json.loads(json_text)
    print(json.dumps(latest_audit_results, indent=4))


if __name__ == "__main__":
    view_eval_result()