Here is the documentation for the provided GitHub Workflows and Composite Actions.

# GitHub Actions & Workflows Documentation

This document outlines the inputs, outputs, and secrets required for the modular workflows and composite actions used in the pipeline.

## 1. Reusable Workflows (Modules)

These workflows are triggered via `workflow_call`.

### Module: Packer Build (AWS)
Builds an AMI using Packer.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `packer_dir` | | String | `./packer/v1` | Directory containing Packer configuration. |
| `matlab_version` | ✓ | String | | The MATLAB version to build. |
| `skip_build` | | Boolean | `false` | Mock the build for testing. |

| Output Name | Description |
| :--- | :--- |
| `ami_id` | The ID of the built AMI. |
| `region` | The region where the AMI was built. |

---

### Module: Patch Template (Single AMI)
Injects a single AMI ID into a CloudFormation template.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `template_path` | ✓ | String | | Path to the CFN template. |
| `ami_id` | ✓ | String | | The AMI ID to inject. |
| `matlab_version` | | String | `""` | Optional MATLAB version context. |

---

### Module: AWS Release Prep
Prepares artifacts for an AWS release.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `version` | ✓ | String | | Release version string. |
| `flavor` | ✓ | String | | Deployment flavor. |
| `ami_id` | ✓ | String | | The AMI ID associated with release. |
| `template_artifact` | ✓ | String | | Artifact name for the template. |
| `packer_artifact` | ✓ | String | | Artifact name for Packer logs/manifests. |
| `matlab_version` | | String | `""` | Optional MATLAB version context. |

---

### Module: AWS Smoke Test
Deploys infrastructure to test validity.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `template_artifact` | ✓ | String | | Name of artifact containing the CFN template. |
| `flavor` | ✓ | String | | Deployment flavor. |
| `region` | | String | `us-east-1` | AWS Region for the test. |
| `matlab_version` | ✓ | String | | MATLAB version being tested. |

| Secret Name | Required | Description |
| :--- | :---: | :--- |
| `AWS_OIDC_ROLE` | ✓ | Role for AWS authentication. |
| `TEST_VPC_ID` | ✓ | VPC ID for test deployment. |
| `TEST_SUBNET_ID` | ✓ | Subnet ID for test deployment. |

---

### Module: Aggregate GitHub Release
Compiles a GitHub Release from artifacts.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `release_tag` | ✓ | String | | Tag to create the release on. |
| `prerelease` | | Boolean | `true` | Whether to mark as prerelease. |

---

### Module: SLSA Attestation
Generates security attestations for the build artifacts.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `template_artifact` | ✓ | String | | Artifact name for the template. |
| `packer_artifact` | ✓ | String | | Artifact name for Packer data. |
| `matlab_version` | | String | | MATLAB version context. |

---

## 2. Orchestrator Workflows

High-level pipelines that manage multiple modules.

### Orchestrator: Multi-version AWS Build Pipeline
Builds and tests multiple MATLAB versions in parallel or sequence.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `matlab_versions` | | String | | Comma-separated list (e.g., `R2025a,R2024b`). Empty = Latest 5. |
| `flavor` | ✓ | String | | Deployment flavor (matlab-linux, ps-linux, etc). |
| `packer_dir` | | String | `./packer/v1` | Directory containing Packer config. |
| `template_dir_pattern` | | String | `./releases/{0}` | Pattern for template directory. |
| `template_file_name` | | String | `aws-matlab-template.json` | Name of the template file. |
| `skip_build` | | Boolean | `false` | Skip actual build steps (dry run). |

---

### Orchestrator: Single Version AWS Pipeline
Pipeline for a specific MATLAB version.

| Input Name | Required | Type | Default | Description |
| :--- | :---: | :--- | :--- | :--- |
| `matlab_version` | ✓ | String | | The specific MATLAB version. |
| `flavor` | ✓ | String | | Deployment flavor. |
| `packer_dir` | | String | | Directory containing Packer config. |
| `template_dir_pattern` | | String | `./releases/{0}` | Pattern for template directory. |
| `template_file_name` | | String | | Name of the template file. |
| `skip_build` | | Boolean | | Skip actual build steps. |

---

## 3. Composite Actions

These are local actions (usually `action.yml`) run within steps.

### Deploy CloudFormation Stack
**Description:** Downloads template, maps parameters, and deploys stack.

| Input Name | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `stack_name` | ✓ | | Name of the CloudFormation stack. |
| `template_artifact` | ✓ | | Name of the GitHub Artifact containing the template. |
| `template_filename` | | `patched-template.json` | Filename inside the artifact. |
| `flavor` | ✓ | | Deployment flavor (e.g., ps-linux). |
| `region` | ✓ | | AWS Region. |
| `vpc_id` | ✓ | | Target VPC ID. |
| `subnet_id` | ✓ | | Target Subnet ID. |
| `key_name` | ✓ | | SSH Key Name. |

| Output Name | Description |
| :--- | :--- |
| `stack_outputs` | JSON string of stack outputs. |

---

### Create AWS Template
**Description:** Generates a CloudFormation template for either Stage (Single AMI) or Release (Region Map).

| Input Name | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `template_path` | ✓ | | Path to the source JSON template. |
| `mode` | ✓ | `stage` | Operation mode: "stage" or "release". |
| `matlab_version` | | `deployment` | MATLAB version prefix for naming (e.g., R2024a). |
| `ami_id` | | | The Single AMI ID (**Required if mode is "stage"**). |
| `region_map` | | | JSON object string for RegionMap (**Required if mode is "release"**). |