from lib.firebase_client import bucket
from lib.openai_client import client
from utils import EvalResult, FunctionAuditResult, JudgeResult, TargetFinding, TargetFindingWithSeverity, call_openai, get_env, get_latest_audit_results, get_projects
import os
import json
from termcolor import colored
from datetime import datetime
from tqdm import tqdm
import asyncio
from tqdm.asyncio import tqdm_asyncio
import time

def get_severity(title: str):
    if title.startswith("[H-"):
        return "high"
    elif title.startswith("[M-"):
        return "medium"
    elif title.startswith("[L-"):
        return "low"
    else:
        return "unknown"


def get_project_targets_with_severity(project_name: str):
    with_severity: list[TargetFindingWithSeverity] = []

    with open(f"./targets/{project_name}/findings.json", "r") as f:
        findings:list[TargetFinding] = json.load(f)["findings"]

        for index, finding in enumerate(findings):
            with_severity.append({
                "id": index,
                "title": finding["title"],
                "description": finding["description"],
                "severity": get_severity(finding["title"])
            })

    return with_severity

async def judge_finding(target_finding: TargetFindingWithSeverity, llm_findings: list[FunctionAuditResult], project_name: str):
    try:
        if len(llm_findings) == 0:
            judge_result = JudgeResult(
                project_name=project_name,
                target_finding=target_finding,
                llm_finding=None,
                is_true_positive=False,
                failed=False
            )

            return judge_result

        prompt = f"""
                This is a vulnerability of a function of a smart contract. 
                Vulnerability: {target_finding['title']}
                Description:    {target_finding['description']}

                Here are the predicted findings:
                {llm_findings}

                If the vulnerability corresponds to any of the predicted findings, return the function_name of the predicted finding.
                If the vulnerability does not correspond to any of the predicted findings, return -1.

                Just return the function_name of the predicted finding or -1. No other text.
                """

        response =  await call_openai(
                model="gpt-5-mini",
                instructions="You are a judge that judges if a vulnerability finding is a true positive or false positive.",
                prompt=prompt,
            )

        matched_target_finding_function_name = response.output_text

        if matched_target_finding_function_name == "-1":
            judge_result = JudgeResult(
                project_name=project_name,
                target_finding=target_finding,
                llm_finding=None,
                is_true_positive=False,
                failed=False
            )
            return judge_result
        else:
            for llm_finding in llm_findings:
                if llm_finding["function_name"] == matched_target_finding_function_name:
                    judge_result = JudgeResult(
                        project_name=project_name,
                        target_finding=target_finding,
                        llm_finding=llm_finding,
                        is_true_positive=True,
                        failed=False
                    )
                    return judge_result

            print(colored(f"No predicted finding found for {matched_target_finding_function_name}", "red"))
            judge_result = JudgeResult(
                project_name=project_name,
                target_finding=target_finding,
                llm_finding=None,
                is_true_positive=False
            )

            return judge_result
    except Exception as e:
        print(colored(f"Error judging finding: {e}", "red"))
        judge_result = JudgeResult(
            project_name=project_name,
            target_finding=target_finding,
            llm_finding=None,
            is_true_positive=False,
            failed=True
        )

        return judge_result

async def judge_project(result: list[FunctionAuditResult], project_name: str):
    target_findings = get_project_targets_with_severity(project_name)
    judge_findings_tasks = []

    llm_project_findings = [llm_finding for llm_finding in result if not llm_finding["safe"] and llm_finding["project_name"] == project_name]

    for target_finding in target_findings:
        judge_findings_tasks.append(judge_finding(target_finding, llm_project_findings, project_name))

    judge_results: list[JudgeResult] = await tqdm_asyncio.gather(*judge_findings_tasks, desc="Judging findings", colour="green")
    
    return judge_results
    """
    true_positives: list[JudgeResult] = [judge_result for judge_result in judge_results if judge_result["is_true_positive"]]
    false_positives: list[FunctionAuditResult] = [judge_result for judge_result in judge_results if judge_result[0] is None]

    true_positive_ids = [judge_result[0]["id"] for judge_result in true_positives]
    true_negatives = [target_finding for target_finding in target_findings if target_finding["id"] not in true_positive_ids]

    num_tn = len(true_negatives) # true negatives
    num_fp = len(false_positives) # false positives
    num_tp = len(true_positives) # true positives
    
    false_positive_rate = num_fp / (num_tn + num_fp) if num_tn + num_fp > 0 else 0
    true_positive_rate = num_tp / (num_tp + num_fp) if num_tp + num_fp > 0 else 0

    print(f"\n{colored(f'Contract: {contract_name}', 'green')}")
    print(f"True negatives: {num_tn}")
    print(f"False positives: {num_fp}")
    print(f"True positives: {num_tp}")
    print(f"False positive rate: {false_positive_rate}")
    print(f"True positive rate: {true_positive_rate}")


    print("False positives:")
    print(false_positives)
    """


def save_judge_results(results: list[JudgeResult]):
    judge_results_dir = f"./judge_results/"
    os.makedirs(judge_results_dir, exist_ok=True)

    now = int(datetime.now().timestamp())

    file_name = f"result-{now}.json"
    with open(f"./judge_results/{file_name}", "w") as f:
        json.dump(results, f, indent=4, default=str)
    
    
    blob = bucket.blob(f"eval-runs-{get_env()}/judge_results/{file_name}")
    blob.upload_from_filename(f"./judge_results/{file_name}", content_type="application/json")
  
if __name__ == "__main__":
    audit_results = get_latest_audit_results()

    projects = list(set([audit_result["project_name"] for audit_result in audit_results]))

    judge_tasks = []
    for project in projects:
        project_audit_results = [audit_result for audit_result in audit_results if audit_result["project_name"] == project]
        judge_tasks.append(judge_project(project_audit_results, project))

    start = time.time()
    judge_results = asyncio.run(tqdm_asyncio.gather(*judge_tasks, desc="Judging projects", colour="green"))
    end = time.time()
    print(f"Judging took: {end - start} seconds")

    save_judge_results(judge_results)

    