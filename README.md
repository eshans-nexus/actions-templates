# GitHub Actions Templates for AWS Infrastructure Pipelines

## Overview

The `actions-templates` repository serves as a centralized library of reusable GitHub Actions workflows and composite actions. It creates a standardized pipeline for building Amazon Machine Images (AMIs), updating CloudFormation templates, performing smoke tests on live infrastructure, and publishing releases.

This design separates pipeline logic from product configuration, allowing consumer repositories (such as `matlab-on-aws-pvt`) to invoke complex workflows with minimal configuration.

## Architecture and Design Decisions

The repository follows a modular architecture orchestrated by a parent workflow.

### 1. The Orchestrator Pattern
**File:** `.github/workflows/orchestrator-aws.yml`

Instead of defining a monolithic workflow in every consumer repository, this system uses a "Caller/Called" pattern. The orchestrator defines the strict sequence of operations required for a release:
1.  **Build:** Create the AMI using Packer.
2.  **Patch:** Inject the new AMI ID into the CloudFormation template.
3.  **Test:** Deploy the infrastructure and verify connectivity.
4.  **Attest:** Generate SLSA provenance.
5.  **Release:** Publish artifacts to GitHub Releases.

**Cost/Benefit:**
*   **Benefit:** Enforces consistency across different products. A security update or logic change in the orchestrator immediately propagates to all consumers.
*   **Cost:** Reduces flexibility for consumer repositories. If a specific product requires a radically different build order, it cannot use this standard orchestrator.

### 2. Deployment Abstraction via "Flavors"
**File:** `.github/actions/deploy-cfn/`

AWS CloudFormation stacks for different products (e.g., Linux vs. Windows, MATLAB vs. License Manager) require vastly different input parameters. Hardcoding these variations into YAML workflows leads to unmaintainable conditional logic.

**Design Decision:**
The logic was moved into a local composite action (`deploy-cfn`) backed by a configuration file (`flavor-mappings.json`).
*   **Flavor Mappings:** A JSON dictionary defines default parameter values and maps generic inputs (like `key_name`) to specific CloudFormation parameter keys (e.g., `SSHKeyName` vs `RDPKeyName`).
*   **Composite Action:** The action takes a `flavor` input, reads the JSON mapping, and constructs the parameter list dynamically using `jq` before triggering the AWS CLI.

**Cost/Benefit:**
*   **Benefit:** Drastically simplifies workflow YAML files. Adding a new product variant only requires updating the JSON file, not the pipeline code.
*   **Cost:** Hidden logic. A developer looking at the workflow YAML cannot immediately see which parameters are being passed to CloudFormation without checking the JSON file.

### 3. Ephemeral Infrastructure Testing
**File:** `.github/workflows/module-aws-smoke-test.yml`

The pipeline performs integration testing by provisioning actual AWS resources rather than using mocks.
1.  Generates a temporary SSH key pair.
2.  Deploys the CloudFormation stack.
3.  Verifies connectivity (SSH for Linux, RDP port check for Windows).
4.  Tears down the stack and deletes the keys.

**Cost/Benefit:**
*   **Benefit:** High confidence. It verifies the AMI, the CloudFormation template, and network security groups in a real-world environment.
*   **Cost:** Increased runner time and AWS infrastructure costs. The workflow must wait for the stack to reach `CREATE_COMPLETE`, which can take several minutes.

## Workflow Modules

### Module: Packer Build (AWS)
**File:** `.github/workflows/module-aws-packer-build.yml`
*   **Function:** Authenticates via OIDC, sets up Packer, and runs the build.
*   **Test Mode:** Includes a `test_mode` input. When enabled, it skips the actual Packer build and returns a hardcoded mock AMI ID. This allows for rapid testing of the pipeline logic without incurring AWS costs or waiting for image creation.
*   **Outputs:** Returns the `ami_id` and `region` for downstream jobs.

### Module: Patch Template
**File:** `.github/workflows/module-aws-patch-template.yml`
*   **Function:** Takes the built AMI ID and the source CloudFormation template. It uses `jq` to inject the AMI ID into the template's `CustomAmiId` parameter default value.
*   **Why:** This creates an immutable artifact. The template deployed during testing and attached to the release is guaranteed to reference the exact AMI built in the previous step.

### Module: SLSA Attest
**File:** `.github/workflows/module-common-slsa-attest.yml`
*   **Function:** Uses `actions/attest-build-provenance` to generate signed attestations for the patched template and build logs.
*   **Purpose:** Supply chain security. It verifies that the artifacts were built by this specific workflow run on GitHub Actions.

### Module: GitHub Release
**File:** `.github/workflows/module-gh-release.yml`
*   **Function:** Creates a draft release (or pre-release) and uploads the patched CloudFormation template, Packer manifest, and build logs.

## Usage Guide

To use these templates in a consumer repository (e.g., `matlab-on-aws-pvt`), creates a workflow that calls the orchestrator.

**Example Configuration:**

```yaml
jobs:
  call-orchestrator:
    uses: eshans-nexus/actions-templates/.github/workflows/orchestrator-aws.yml@main
    with:
      matlab_version: 'R2025a'
      flavor: 'matlab-linux' # Must match a key in flavor-mappings.json
      packer_dir: './packer/v1'
      template_dir_pattern: './releases/{0}'
      template_file_name: 'aws-matlab-template.json'
    secrets: inherit # Required to pass AWS OIDC and Test VPC secrets
```

### Prerequisites
The consuming repository must have the following secrets configured:
1.  `AWS_OIDC_ROLE`: The IAM role ARN for OIDC authentication.
2.  `TEST_VPC_ID`: The VPC ID where smoke tests will run.
3.  `TEST_SUBNET_ID`: The Subnet ID where smoke tests will run.

### Adding New Flavors
If a new product type is introduced (e.g., a new License Manager configuration), update `.github/actions/deploy-cfn/flavor-mappings.json` in the `actions-templates` repository.

1.  Define the `key_param` (SSH or RDP key parameter name).
2.  Define the `vpc_param` and `subnet_param` keys.
3.  Provide `defaults` for other required CloudFormation parameters.

```json
"new-flavor": {
  "key_param": "KeyName",
  "vpc_param": "VpcId",
  "subnet_param": "SubnetId",
  "client_ip_param": "RemoteAccessCIDR",
  "defaults": [
    { "ParameterKey": "InstanceSize", "ParameterValue": "m5.large" }
  ]
}
```