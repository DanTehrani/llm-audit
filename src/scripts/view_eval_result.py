from lib.firebase_client import bucket
from utils import FunctionAuditResult, get_env
import json
from termcolor import colored


#env = get_env()
env = "prod"

def view_eval_result():
    prefix = f"eval-runs-{env}/audit_results"          # folder you want to inspect

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
    blob = bucket.blob(f"{prefix}/audit-{latest_audit_timestamp}.json")
    json_text = blob.download_as_text()

    latest_audit_results: list[FunctionAuditResult] = json.loads(json_text)
    for latest_audit_result in latest_audit_results:
        print(colored(latest_audit_result["project_name"], "green"))
        print(colored(latest_audit_result["function_name"], "green"))
        print(f"Safe: {colored(latest_audit_result['safe'], 'green' if latest_audit_result['safe'] else 'red')}")
        print("")
        print(latest_audit_result["reason"])
        print("")
        print(latest_audit_result["description"])
        print(latest_audit_result["proposedFix"])
        print(latest_audit_result["failed"])
        print("--------------------------------")


if __name__ == "__main__":
    view_eval_result()