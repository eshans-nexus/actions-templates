
## Deploy CFN (`actions/deploy-cfn`)

### Overview

This action deploys an ephemeral CloudFormation stack for integration and smoke testing. To avoid massive, brittle conditional blocks in our workflow YAMLs, this action utilizes a "Flavor Mapping" pattern. It dynamically constructs CloudFormation parameters based on the specific architecture being deployed (e.g., Linux vs. Windows, Single Node vs. Parallel Server).

### The Workflow

1. **Flavor Resolution:** Reads `flavor-mappings.json` to lookup the default parameter values and variable names (like identifying whether to use `SSHKeyName` or `RDPKeyName`) for the requested `flavor`.
2. **Dynamic Parameter Injection:** Fetches the GitHub Runner's current IP address and injects it, along with standard inputs (VPC, Subnet, SSH Key), into a generated `params.json` file.
3. **Execution:** Triggers `aws cloudformation create-stack` and blocks until the `stack-create-complete` signal is received.
4. **Data Retrieval:** Parses the final CloudFormation stack outputs into a flattened JSON key-value string.

### Inputs & Outputs

| Input | Required | Description |
| --- | --- | --- |
| `template_file_path` | Yes | Path to the compiled CloudFormation template. |
| `flavor` | Yes | Target deployment flavor matching a key in `flavor-mappings.json`. |
| `region` | Yes | AWS region to deploy the stack into. |
| `stack_name` | Yes | Unique identifier for the temporary stack. |
| `vpc_id` / `subnet_id` | Yes | Network configuration for the deployment. |
| `key_name` | Yes | Name of the pre-provisioned AWS Key Pair for access. |

**Outputs:**

* `stack_outputs`: A flat JSON string of the CloudFormation stack outputs (e.g., `{"HeadnodePublicDNS": "ec2-...", "RDPConnection": "..."}`).

### Example Usage

```yaml
- name: Deploy Ephemeral Stack
  id: deploy
  uses: eshans-nexus/actions-templates/.github/actions/deploy-cfn@main
  with:
    template_file_path: './R2025a-test-template.json'
    flavor: 'matlab-linux'
    region: 'us-east-1'
    stack_name: 'smoke-test-stack-12345'
    vpc_id: 'vpc-0abcd1234'
    subnet_id: 'subnet-0abcd1234'
    key_name: 'smoke-test-key-12345'

```

