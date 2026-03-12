import boto3
import argparse
import json
import time
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Run Trivy via AWS SSM")
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--os-type", required=True, choices=["linux", "windows"])
    parser.add_argument("--asset-name", default="Target Asset")
    parser.add_argument("--timeout-minutes", type=int, default=10)
    parser.add_argument("--config", default="scan_config.json")
    args = parser.parse_args()

    # Load Config
    with open(args.config, "r") as f:
        config = json.load(f)
    
    os_config = config.get(args.os_type)
    if not os_config:
        print(f"::error::OS type {args.os_type} not found in config.")
        sys.exit(1)

    ssm = boto3.client("ssm")
    
    print(f"Sending Trivy scan commands to {args.os_type} instance {args.instance_id}...")
    try:
        response = ssm.send_command(
            InstanceIds=[args.instance_id],
            DocumentName=os_config["document_name"],
            Parameters={"commands": os_config["commands"]}
        )
        command_id = response["Command"]["CommandId"]
    except Exception as e:
        print(f"::error::Failed to send SSM command: {e}")
        sys.exit(1)

    print(f"Command ID: {command_id}. Waiting for execution to finish...")
    
    timeout_seconds = args.timeout_minutes * 60
    start_time = time.time()
    status = "Pending"
    
    # Custom Waiter Loop
    while status in ["Pending", "InProgress", "Delayed"]:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"::error::SSM Command timed out after {args.timeout_minutes} minutes.")
            ssm.cancel_command(CommandId=command_id, InstanceIds=[args.instance_id])
            sys.exit(1)
            
        time.sleep(15)
        
        try:
            invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=args.instance_id
            )
            status = invocation["Status"]
            print(f"Current status: {status} (Elapsed: {int(elapsed)}s / {timeout_seconds}s)")
        except Exception as e:
            # Handle eventual consistency where invocation isn't immediately available
            print(f"Waiting for command invocation to register...")
            pass

    if status != "Success":
        print(f"::error::SSM Command failed with status: {status}")
        
        # Fetch and print the actual error logs from the instance
        print("Fetching error logs from SSM...")
        try:
            error_invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=args.instance_id
            )
            print("\n=== STANDARD ERROR ===")
            print(error_invocation.get("StandardErrorContent", "No error output provided."))
            print("\n=== STANDARD OUTPUT ===")
            print(error_invocation.get("StandardOutputContent", "No standard output provided."))
        except Exception as e:
            print(f"Could not retrieve error logs: {e}")
            
        sys.exit(1)

    print("Fetching processed Markdown output...")
    try:
        final_invocation = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=args.instance_id
        )
        output_content = final_invocation.get("StandardOutputContent", "").strip()
    except Exception as e:
        print(f"::error::Failed to fetch final output: {e}")
        sys.exit(1)

    if not output_content:
        print("::warning::SSM command returned empty output. The scan may have failed silently.")
        output_content = "No output returned from scan."
    # -----------------------------------

    # Write directly to the Step Summary
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as f:
            f.write(f"## 🛡️ Trivy Security Scan Results\n")
            f.write(f"**Asset:** `{args.asset_name}` | **OS:** `{args.os_type}`\n\n")
            f.write(output_content + "\n")
    else:
        # Fallback for local testing if GITHUB_STEP_SUMMARY is not set
        print("\n## 🛡️ Trivy Security Scan Results")
        print(f"**Asset:** `{args.asset_name}` | **OS:** `{args.os_type}`\n")
        print(output_content)
    
    print("Scan complete. Summary generated.")

if __name__ == "__main__":
    main()