"""
Persistence utilities for saving patient bundles to disk.
"""

import json


def persist_patient_bundles(patient_bundles, output_dir, resources_map):
    """
    Persist patient bundles to FHIR JSON files.
    
    Args:
        patient_bundles: Dictionary mapping patient_id to {'resources': set, 'resource_objects': []}
        output_dir: Path object for output directory
        resources_map: Dictionary mapping resource types to resources
    
    Returns:
        Number of bundles persisted
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for patient_id, bundle_data in patient_bundles.items():
        patient_uuid = patient_id.split("/")[1]
        resource_objects = bundle_data["resource_objects"]
        
        resource_objects.sort(
            key=lambda r: (
                0 if r["resourceType"] == "Patient" else 1,
                r["resourceType"]
            )
        )
        
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": resource}
                for resource in resource_objects
            ]
        }

        output_file = output_dir / f"{patient_uuid}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                fhir_bundle,
                f,
                indent=2,
                ensure_ascii=False
            )
    
    return len(patient_bundles)
