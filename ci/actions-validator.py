#!/usr/bin/env python3
import sys
import os
import yaml
import json

def validate_yaml(file_path):
    print(f"Validating {file_path}")
    try:
        with open(file_path, "r") as f:
            yaml_content = yaml.safe_load(f)
            # If we got here, the YAML is valid
            print(f"✅ {file_path} is valid YAML")
            return True
    except yaml.YAMLError as e:
        print(f"❌ {file_path} has YAML syntax errors:")
        print(f"   {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <workflow_file> [workflow_file...]")
        sys.exit(1)

    result = 0
    for file_arg in sys.argv[1:]:
        # Handle glob patterns
        import glob
        files = glob.glob(file_arg)
        if not files:
            print(f"No files match pattern: {file_arg}")
            result = 1
            continue

        for file_path in files:
            if not os.path.isfile(file_path):
                print(f"File not found: {file_path}")
                result = 1
                continue

            if not validate_yaml(file_path):
                result = 1

    sys.exit(result)