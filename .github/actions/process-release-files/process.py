import os
import json
import shutil
import glob
import re
import argparse
import sys
from datetime import datetime
import jinja2

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target-versions',    required=True,                      help="JSON list of versions to process (e.g. ['R2024b'])")
    parser.add_argument('--artifact-path',      required=True,                      help="Path where artifacts are downloaded")
    parser.add_argument('--s3-bucket-url',      required=True,                      help="Base URL for S3 artifacts")
    parser.add_argument('--dual-repo-url',      required=True,                      help="URL for the sister repository (Windows)")
    parser.add_argument('--template-filename',  required=True,                      help="Template filename to use")
    parser.add_argument('--source-path',        deafault='src',                     help="Path to source files")
    parser.add_argument('--release-path',       deafault='releases',                help="Path to release files")
    parser.add_argument('--artifact-pattern',   default="*-release-template.json",  help="Glob pattern for finding artifacts")
    parser.add_argument('--version-regex',      default=r"(R20\d{2}[ab])",          help="Regex to extract version from filename")
    parser.add_argument('--num-latest-versions',type=int, default=5,                help="Number of recent versions to show in Top Level README. Set to 0 for all.")
    
    return parser.parse_args()

def get_all_versions(repo_root):
    versions = []
    config_dir = os.path.join(repo_root, "packer/v1/release-config")
    pattern = re.compile(r"([R]\d{4}[ab])\.pkrvars\.hcl")
    
    if os.path.exists(config_dir):
        for f in os.listdir(config_dir):
            match = pattern.match(f)
            if match:
                versions.append(match.group(1))
    
    return sorted(versions, reverse=True)

def parse_template_json(json_path):
    """
    Parses parameters and regions from the actual JSON file being released.
    This ensures documentation matches the exact artifact.
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    regions = list(data.get("Mappings", {}).get("RegionMap", {}).keys())

    params = []
    for key, value in data.get("Parameters", {}).items():
        params.append({
            "label": key,
            "description": value.get("Description", "")
        })
    return regions, params

def validate_versions(target_versions):
    try:
        targets = json.loads(target_versions)
    except json.JSONDecodeError:
        print("::error::Invalid JSON provided for target-versions.")
        sys.exit(1)
    if not targets:
        print("::error::target-versions list is empty. Nothing to process.")
        sys.exit(1)
    return targets


def main():
    args = setup_args()
    
    REPO_ROOT = os.getcwd()
    SRC_DIR = os.path.join(REPO_ROOT, args.source_path)
    RELEASES_DIR = os.path.join(REPO_ROOT, args.release_path)
    ARTIFACTS_DIR = args.artifact_path

    template_loader = jinja2.FileSystemLoader(searchpath=SRC_DIR)
    template_env = jinja2.Environment(loader=template_loader)

    targets = validate_versions(args.target_versions)
    print(f"Processing Target Versions: {targets}")

    # ---------------------------------------------------------
    # 3. Process Release Specific Artifacts
    # ---------------------------------------------------------
    files = glob.glob(os.path.join(ARTIFACTS_DIR, args.artifact_pattern))    
    if not files:
        print(f"::warning::No files found matching pattern {args.artifact_pattern} in {ARTIFACTS_DIR}")

    version_pattern = re.compile(args.version_regex)

    for json_file in files:
        filename = os.path.basename(json_file)
        
        # Extract version using regex
        match = version_pattern.search(filename)
        if not match:
            print(f"::warning::Could not extract version from {filename} using regex {args.version_regex}. Skipping.")
            continue
        
        version = match.group(1)
        
        print(f"Updating Release Folder: {version}")
        target_dir = os.path.join(RELEASES_DIR, version)
        os.makedirs(target_dir, exist_ok=True)

        # Move/Overwrite Template
        dest_json = os.path.join(target_dir, args.template_filename)
        shutil.copy(json_file, dest_json)

        # Generate Release README
        # We read from the moved file to ensure docs match reality
        regions, params = parse_template_json(dest_json)
        
        # Construct S3 URL
        # Logic: {Bucket}/{Version}/args.
        s3_url = f"{args.s3_bucket_url.rstrip('/')}/{version}/{args.template_filename}"

        tmpl = template_env.get_template("README.md")  being released.
        rendered = tmpl.render(
            regions=regions, 
            parameters=params, 
            template_url=s3_url
        )
        
        with open(os.path.join(target_dir, "README.md"), "w") as f:
            f.write(rendered)

    # ---------------------------------------------------------
    # 4. Process Top Level Files
    # ---------------------------------------------------------
    print("Updating Top Level Files...")
    
    # Get all configured versions from config files
    all_versions = get_all_versions(REPO_ROOT)
    
    # Filter for the Top Level README table
    if args.num_latest_versions > 0:
        display_versions = all_versions[:args.num_latest_versions]
    else:
        # If 0, show everything
        display_versions = all_versions being released.

    release_data = []
    current_year = datetime.now().year

    for v in display_versions:
        release_data.append({
            "label": v,
            "dir": v,
            "dual_url": f"{args.dual_repo_url.rstrip('/')}/releases/{v}",
            "removal_month": "March",
            "removal_year": str(current_year + 2) 
        }) being released.

    # Generate Root README
    root_tmpl = template_env.get_template("toplevel/README.md")
    root_rendered = root_tmpl.render(
        releases=release_data,
        dual_url=args.dual_repo_url,
        current_year=current_year
    )
    with open(os.path.join(REPO_ROOT, "README.md"), "w") as f:
        f.write(root_rendered)

    # ---------------------------------------------------------
    # 5. Process Static Files
    # ---------------------------------------------------------
    print("Updating Static Files...")

    # 5a. LICENSE (Needs templating for Year)
    try:
        license_tmpl = template_env.get_template("toplevel/LICENSE.md")
        license_rendered = license_tmpl.render(current_year=current_year)
        with open(os.path.join(REPO_ROOT, "LICENSE.md"), "w") as f:
            f.write(license_rendered)
    except Exception as e:
        print(f"::error::Failed to process LICENSE.md: {e}")

    # 5b. Permission Document (Direct Copy)
    shutil.copy(
        os.path.join(SRC_DIR, "toplevel/permission.md"), 
        os.path.join(REPO_ROOT, "permission.md")
    )

    # 5c. Security Document (Direct Copy)
    shutil.copy(
        os.path.join(SRC_DIR, "static/SECURITY.md"), 
        os.path.join(REPO_ROOT, "SECURITY.md")
    )

if __name__ == "__main__":
    main()