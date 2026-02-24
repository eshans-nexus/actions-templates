
## Create AWS Template (`actions/create-aws-template`)

### Overview

This action acts as the template compiler for our CloudFormation infrastructure. It takes a generic, region-agnostic meta-template and a JSON RegionMap, merges them using `jq`, and produces a valid, deployable CloudFormation JSON artifact.

### The Workflow

1. **Dependency Verification:** Ensures `jq` is installed on the runner.
2. **Injection:** Reads the provided `region_map` string and securely injects it into the `.Mappings.RegionMap` block of the source meta-template. This overrides any placeholder mappings.
3. **Artifact Publishing:** Uploads the newly generated CloudFormation template as a GitHub Actions artifact for downstream jobs (like deployment or release aggregation) to consume.

### Inputs & Outputs

| Input | Required | Description |
| --- | --- | --- |
| `region_map` | Yes | The JSON string containing region-to-AMI mappings. |
| `output_filename` | Yes | The desired filename for the compiled template. |
| `artifact_name` | Yes | The name under which to upload the GitHub artifact. |
| `metatemplate_file_path` | Yes | Relative path to the source JSON meta-template. |

### Example Usage

```yaml
- name: Generate CloudFormation Template
  uses: eshans-nexus/actions-templates/.github/actions/create-aws-template@main
  with:
    region_map: '{"us-east-1": {"AMI": "ami-0123456789abcdef0"}}'
    output_filename: 'R2025a-release-template.json'
    artifact_name: 'R2025a-release-template'
    metatemplate_file_path: 'src/meta-template.json'

```

