
## Run Trivy Scan (`actions/run-trivy-scan`)

### Overview

This action performs a runtime security audit on a provisioned EC2 instance. It uses AWS Systems Manager (SSM) `SendCommand` to drive the [Trivy](https://github.com/aquasecurity/trivy) vulnerability scanner on the target, captures the JSON report, and renders a Markdown summary into the GitHub Actions Step Summary UI.

### The Workflow

1. **Command Dispatch:** Reads OS-specific command sets from `scan_config.json` and sends them to the target via `ssm.send_command`. Linux uses `AWS-RunShellScript`; Windows uses `AWS-RunPowerShellScript`.
2. **OS-Specific Execution:**
   * **Linux:** Installs Trivy via the upstream `install.sh` script pinned to a fixed version, runs `trivy fs /` for HIGH/CRITICAL fixable vulnerabilities, and renders the JSON to a Markdown table with `jq`.
   * **Windows:** Downloads the version-pinned Trivy zip, expands it to `C:\trivy`, runs `trivy fs C:\`, and renders the JSON to Markdown in PowerShell.
3. **Polling:** Polls `ssm.get_command_invocation` until the command reaches a terminal state or `timeout_minutes` is exceeded; cancels the command on timeout.
4. **Aggregation:** Writes the rendered Markdown table to `$GITHUB_STEP_SUMMARY`.

### Prerequisites

* The runner must have AWS credentials configured with permission to call `ssm:SendCommand`, `ssm:GetCommandInvocation`, and `ssm:CancelCommand` on the target instance.
* The target EC2 instance must have the SSM Agent running and an instance profile that allows it to register with SSM.

### Inputs & Outputs

| Input | Required | Description |
| --- | --- | --- |
| `instance_id` | Yes | EC2 instance ID of the target (for example `i-0123456789abcdef0`). |
| `os_type` | Yes | Target operating system (`linux` or `windows`). |
| `asset_name` | No | Contextual name (such as the AMI ID) shown in the report header. |
| `timeout_minutes` | No | Maximum minutes to wait for the SSM command to complete. Defaults to `10`. |

### Example Usage

```yaml
- name: Execute Security Scan
  uses: mathworks-ref-arch/iac-building-blocks/.github/actions/run-trivy-scan@main
  with:
    instance_id: 'i-0123456789abcdef0'
    os_type: 'linux'
    asset_name: 'ami-0123456789abcdef0'
    timeout_minutes: '15'
```
