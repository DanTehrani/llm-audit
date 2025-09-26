import os
import json
from utils import TargetFinding, TargetFindingWithSeverity

targets_list = os.listdir("./targets")

def get_severity(title: str):
    if title.startswith("[H-"):
        return "high"
    elif title.startswith("[M-"):
        return "medium"
    elif title.startswith("[L-"):
        return "low"
    else:
        return "unknown"

total_high_findings = 0
total_medium_findings = 0

for project in targets_list:
    with open(f"./targets/{project}/findings.json", "r") as f:
        findings: list[TargetFinding] = json.load(f)["findings"]
        print(project, len(findings))

        total_high_findings += len([f for f in findings if get_severity(f["title"]) == "high"])
        total_medium_findings += len([f for f in findings if get_severity(f["title"]) == "medium"])

print(total_high_findings)
print(total_medium_findings)