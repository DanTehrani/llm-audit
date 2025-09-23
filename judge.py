from openai_client import client
from utils import FunctionAuditResult, TargetFinding
import os
import json
from termcolor import colored
from datetime import datetime

PROJECT_NAME= "2025-04-virtuals-protocol"
TARGET_FINDINGS_PATH = f"./targets/{PROJECT_NAME}/findings.json"

with open(TARGET_FINDINGS_PATH, "r") as f:
    target_findings: list[TargetFinding] = json.load(f)

def judge(result: list[FunctionAuditResult], contract_name: str):
    matched_target_findings: list[int] = []
    false_positives: list[FunctionAuditResult] = []

    for llm_finding in result:
        if llm_finding['safe']:
            # Don't judge safe findings
            continue

        print(f"Judging {llm_finding['description']}")

        response = client.responses.create(
            model="o3-mini",
            instructions="You are a judge that judges if a vulnerability finding is a true positive or false positive.",
            input=f"""
            This is a predicted vulnerability finding about a function of a smart contract. 
            Function name: {llm_finding['function_name']}
            Reason:    {llm_finding['reason']}
            Description: {llm_finding['description']}

            Here are the target (i.e. correct) findings:
            {target_findings}

            If the predicted finding corresponds to any of the target findings, return the id of the target finding.
            If the predicted finding does not correspond to any of the target findings, return -1.

            Just return the id of the target finding or -1. No other text.
            """,
        )

        matched_target_finding = int(response.output_text)

        if matched_target_finding != -1:
            matched_target_findings.append(matched_target_finding)
        else:
            false_positives.append(llm_finding)
    
    num_tn = len(target_findings) - len(matched_target_findings) # true negatives
    num_fp = len(false_positives) # false positives
    num_tp = len(matched_target_findings) # true positives
    
    false_positive_rate = num_fp / (num_tn + num_fp) if num_tn + num_fp > 0 else 0
    true_positive_rate = num_tp / (num_tp + num_fp) if num_tp + num_fp > 0 else 0

    print(f"\n{colored(f'Contract: {contract_name}', 'green')}")
    print(f"True negatives: {num_tn}")
    print(f"False positives: {num_fp}")
    print(f"True positives: {num_tp}")
    print(f"False positive rate: {false_positive_rate}")
    print(f"True positive rate: {true_positive_rate}")

    print("Matched target findings:")
    print(matched_target_findings)

    print("False positives:")
    print(false_positives)


if __name__ == "__main__":
    audited_contracts = os.listdir("./audits/contracts/")
    
    for audited_contract in audited_contracts:
        contract_audits = os.listdir(f"./audits/contracts/{audited_contract}")
        latest_audit = contract_audits[-1]        

        with open(f"./audits/contracts/{audited_contract}/{latest_audit}", "r") as f:
            audit_result: list[FunctionAuditResult] = json.load(f)

        if audited_contract != "AgentNftV2":
            continue

        with open(f"./audits/contracts/{audited_contract}/{latest_audit}", "r") as f:
            audit_result: list[FunctionAuditResult] = json.load(f)

        print(f"Audited results: {audit_result}")
        judge(audit_result, audited_contract)