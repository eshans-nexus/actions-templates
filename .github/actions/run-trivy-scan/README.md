
## Run Trivy Scan (`actions/run-trivy-scan`)

### Overview

This action performs a runtime security audit on our provisioned infrastructure. It connects to the live EC2 instance via SSH, installs the Trivy vulnerability scanner on the fly, and performs a deep filesystem scan for HIGH and CRITICAL vulnerabilities.

### The Workflow

1. **Network Prep:** Blindly adds the target host to the runner's `known_hosts` to bypass interactive SSH prompts.
2. **OS-Specific Execution:**
* **Linux:** Uses standard Bash over SSH to curl the Trivy install script and execute the scan directly to a JSON file.
* **Windows:** Pipes a PowerShell script over SSH to download the Trivy ZIP, expand it, execute the scan, and return the JSON output.


3. **Aggregation:** Parses the raw JSON report using `jq` to generate a Markdown table, which is then injected directly into the GitHub Actions Step Summary UI for immediate visibility.

### Inputs & Outputs

| Input | Required | Description |
| --- | --- | --- |
| `hostname` | Yes | IP or DNS of the live EC2 instance. |
| `username` | Yes | SSH Username (`ubuntu` or `Administrator`). |
| `ssh_key_path` | Yes | Path to the private key for authentication. |
| `os_type` | Yes | Target operating system (`linux` or `windows`). |
| `asset_name` | No | Contextual name (like the AMI ID) for the report header. |

### Example Usage

```yaml
- name: Execute Security Scan
  uses: development/iac-building-blocks/.github/actions/run-trivy-scan@main
  with:
    hostname: 'ec2-198-51-100-1.compute-1.amazonaws.com'
    username: 'ubuntu'
    ssh_key_path: './private_key.pem'
    os_type: 'linux'
    asset_name: 'ami-0123456789abcdef0'

```

