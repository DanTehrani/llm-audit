import os
import subprocess

if __name__ == "__main__":
    print("Moving files to sources")
    repos = os.listdir("/Users/danieltehrani/dev/repos")    
    print(f"Found {len(repos)} repos")
    sources_path = "/Users/danieltehrani/dev/sources"

    for repo in repos[:1]:
        flattened_path = f"/Users/danieltehrani/dev/repos/{repo}/flattened"
        flattened_with_impls_path = f"/Users/danieltehrani/dev/repos/{repo}/flattened_with_impls"

        scope_path = f"/Users/danieltehrani/dev/repos/{repo}/scope.txt"
        README_PATH = f"/Users/danieltehrani/dev/repos/{repo}/README.md"

        repo_sources_path = f"{sources_path}/{repo}"
        os.makedirs(repo_sources_path, exist_ok=True)

        print(f"Copying {flattened_path} to {repo_sources_path}")
        result = subprocess.run(f"cp -r {flattened_path} {repo_sources_path}", shell=True, capture_output=True, text=True)
        print(result.stdout, result.stderr)

        print(f"Copying {flattened_with_impls_path} to {repo_sources_path}")
        result = subprocess.run(f"cp -r {flattened_with_impls_path} {repo_sources_path}", shell=True, capture_output=True, text=True)
        print(result.stdout, result.stderr)

        print(f"Copying {scope_path} to {repo_sources_path}")
        result = subprocess.run(f"cp {scope_path} {repo_sources_path}", shell=True, capture_output=True, text=True)
        print(result.stdout, result.stderr)

        print(f"Copying {README_PATH} to {repo_sources_path}")
        result = subprocess.run(f"cp {README_PATH} {repo_sources_path}", shell=True, capture_output=True, text=True)
        print(result.stdout, result.stderr)


