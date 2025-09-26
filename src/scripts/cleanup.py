import os

def cleanup():
    repos = os.listdir("/Users/danieltehrani/dev/repos")    

    for repo in repos:
        flattened_path = f"/Users/danieltehrani/dev/repos/{repo}/flattened"
        flattened_with_impls_path = f"/Users/danieltehrani/dev/repos/{repo}/flattened_with_impls"


