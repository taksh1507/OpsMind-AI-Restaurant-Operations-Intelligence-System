"""ML Model Versioning & Manifest Management Utility.

Handles scanning the models directory for existing pkl files, incrementing
versions, reading/writing tenant model manifests, and locating the latest model paths.
"""

import os
import re
import json
from datetime import datetime, timezone

def get_next_version(tenant_id: int, model_type: str) -> int:
    """Scan the tenant's model directory and determine the next version number.
    
    Args:
        tenant_id: Tenant identifier
        model_type: 'forecast' or 'segmentation'
        
    Returns:
        int: Next version number (starts at 1)
    """
    model_dir = os.path.join("models", str(tenant_id))
    if not os.path.exists(model_dir):
        return 1
        
    prefix = "forecast" if model_type == "forecast" else "segments"
    pattern = re.compile(rf"^{prefix}_v(\d+)\.pkl$")
    max_v = 0
    
    for f in os.listdir(model_dir):
        match = pattern.match(f)
        if match:
            max_v = max(max_v, int(match.group(1)))
            
    return max_v + 1

def update_manifest(tenant_id: int, model_type: str, filename: str) -> dict:
    """Update and write manifest.json for the specified tenant and model type.
    
    Args:
        tenant_id: Tenant identifier
        model_type: 'forecast' or 'segmentation'
        filename: Name of the newly saved model file (e.g. forecast_v2.pkl)
        
    Returns:
        dict: The updated manifest data
    """
    model_dir = os.path.join("models", str(tenant_id))
    os.makedirs(model_dir, exist_ok=True)
    manifest_path = os.path.join(model_dir, "manifest.json")
    
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
            
    manifest[model_type] = filename
    manifest["last_trained"] = datetime.now(timezone.utc).isoformat()
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
        
    return manifest

def get_latest_model_path(tenant_id: int, model_type: str, fallback_filename: str) -> str:
    """Retrieve the path to the latest model as recorded in the tenant's manifest.
    
    If the manifest doesn't exist, has no entry, or the file doesn't exist,
    returns the fallback filename path.
    
    Args:
        tenant_id: Tenant identifier
        model_type: 'forecast' or 'segmentation'
        fallback_filename: Fallback filename (e.g. 'forecast_v1.pkl')
        
    Returns:
        str: Absolute or relative path to the model file
    """
    model_dir = os.path.join("models", str(tenant_id))
    manifest_path = os.path.join(model_dir, "manifest.json")
    
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            filename = manifest.get(model_type)
            if filename:
                full_path = os.path.join(model_dir, filename)
                if os.path.exists(full_path):
                    return full_path
        except Exception:
            pass
            
    return os.path.join(model_dir, fallback_filename)
