# Copyright 2026 The MathWorks, Inc.
import os
import json
import boto3
import time
import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ami-id', required=True)
    parser.add_argument('--src-region', required=True)
    parser.add_argument('--dest-regions', required=True, help="Comma separated list")
    parser.add_argument('--version', required=True, help="Matlab version for naming")
    parser.add_argument('--refarch-type', required=True, help="Refarch type for naming")
    parser.add_argument('--test-mode', action='store_true')
    return parser.parse_args()

def main():
    args = get_args()
    
    src_ami = args.ami_id
    src_region = args.src_region
    dest_regions = [r.strip() for r in args.dest_regions.split(',') if r.strip()]
    
    # Initialize RegionMap with the source
    region_map = {
        src_region: {"AMI": src_ami}
    }

    if args.test_mode:
        print(f"::notice::Running in TEST MODE. No resources will be created.")
        for region in dest_regions:
            if region == src_region: continue
            # Return a mock or the source AMI for all regions to validate template generation
            region_map[region] = {"AMI": f"ami-test-{region}"}
        
        final_json = json.dumps({'RegionMap': region_map})
        print(f"Test mode Region Map: {final_json}")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write(f"region_map_json={final_json}\n")
        return

    pending_regions = []

    for dest_region in dest_regions:
        if dest_region == src_region:
            continue

        print(f"Processing region: {dest_region}...")
        
        ec2 = boto3.client('ec2', region_name=dest_region)

        all_amis = ec2.describe_images(Owners=['self'])
        
        dest_ami_id = None
        
        for image in all_amis['Images']:
            if 'Description' in image and f"[Copied {src_ami} from {src_region}]" in image['Description']:
                dest_ami_id = image['ImageId']
                print(f"Found existing copy in {dest_region}: {dest_ami_id}")
                
                if not image.get('Public', False):
                    print(f"Making existing AMI {dest_ami_id} public...")
                    ec2.modify_image_attribute(
                        ImageId=dest_ami_id,
                        LaunchPermission={"Add": [{"Group": "all"}]}
                    )
                break
        
        if not dest_ami_id:
            print(f"Copying {src_ami} to {dest_region}...")
            response = ec2.copy_image(
                Description=f"[Copied {src_ami} from {src_region}]",
                Name=f"{args.version}-{args.refarch_type}-{int(time.time())}",
                SourceImageId=src_ami,
                SourceRegion=src_region
            )
            dest_ami_id = response['ImageId']
            pending_regions.append((dest_region, dest_ami_id))
        
        region_map[dest_region] = {"AMI": dest_ami_id}

    if pending_regions:
        print(f"Waiting for AMIs to become available in: {[x[0] for x in pending_regions]}")
        
    for dest_region, dest_ami in pending_regions:
        print(f"Waiting for {dest_ami} in {dest_region}...")
        ec2 = boto3.client('ec2', region_name=dest_region)
        
        waiter = ec2.get_waiter('image_available')
        # Wait up to 30 mins (45 attempts * 40s)
        waiter.wait(
            ImageIds=[dest_ami],
            WaiterConfig={'Delay': 40, 'MaxAttempts': 45}
        )

        print(f"AMI {dest_ami} is available. Setting permissions...")
        
        # Make AMI Public
        ec2.modify_image_attribute(
            ImageId=dest_ami, 
            LaunchPermission={"Add": [{"Group": "all"}]}
        )

        # Make Snapshot Public
        ami_details = ec2.describe_images(ImageIds=[dest_ami])
        if ami_details['Images']:
            block_mappings = ami_details['Images'][0].get('BlockDeviceMappings', [])
            for mapping in block_mappings:
                if 'Ebs' in mapping and 'SnapshotId' in mapping['Ebs']:
                    snap_id = mapping['Ebs']['SnapshotId']
                    ec2.modify_snapshot_attribute(
                        SnapshotId=snap_id,
                        CreateVolumePermission={"Add": [{"Group": "all"}]}
                    )

    final_json = json.dumps({'RegionMap': region_map})
    print(f"Final Region Map: {final_json}")

    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        fh.write(f"region_map_json={final_json}\n")

if __name__ == "__main__":
    main()