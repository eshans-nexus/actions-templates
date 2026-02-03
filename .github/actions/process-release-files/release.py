import utils
import os

def process_readme(template_env, regions, parameters, template_url, version, readme_path):
    """
    Loads the README template and renders it with release data.
    """
    template = template_env.get_template(readme_path)
    
    return template.render(
        regions         = regions,
        parameters      = parameters,
        template_url    = template_url,
        version         = version
    )

def process_single_release(template_env, version, artifact_dir, s3_bucket_url, release_readme_template_path):
    """
    Processes a single release: finds the CF template, parses it, renders the README.
    
    Returns:
        dict: {
            'version': version, 
            'readme_content': str, 
            'cf_template_content': str, 
        }
    """
    cf_filename = f"{version}-release-template.json"
    cft_path = os.path.join(artifact_dir, cf_filename)
    
    if not os.path.exists(cft_path):
        print(f"Warning: Artifact for {version} not found at {cft_path}")
        return None
    
    regions, parameters = utils.parse_template_json(cft_path)
    template_url = f"{s3_bucket_url.rstrip('/')}/{version}/{cf_filename}"
    
    readme_content = process_readme(
        template_env    = template_env,
        regions         = regions,
        parameters      = parameters,
        template_url    = template_url,
        version         = version,
        readme_path     = release_readme_template_path
        )

    # 5. Read the Raw CF Template Content (to save it later)
    with open(cft_path, 'r', encoding='utf-8') as f:
        cft_content = f.read()

    return {
        'version': version,
        'readme_content': readme_content,
        'cf_template_content': cft_content,
    }

def process_files(template_env, target_versions, artifact_dir, s3_bucket_url, release_readme_template_path):
    release_outputs = []
    
    for version in target_versions:
        result = process_single_release(
            template_env, 
            version, 
            artifact_dir, 
            s3_bucket_url, 
            release_readme_template_path
        )
        if result:
            release_outputs.append(result)
            
    return release_outputs