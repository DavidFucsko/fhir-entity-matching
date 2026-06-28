from collections import defaultdict
from pathlib import Path
import json
import gzip
import os


def find_references(obj, references=None):
    if references is None:
        references = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "reference" and isinstance(value, str):
                references.append(value)
            else:
                find_references(value, references)
    elif isinstance(obj, list):
        for item in obj:
            find_references(item, references)
    
    return references


def build_fhir_graphs(fhir_path=None):
    if fhir_path is None:
        dirname = os.getcwd()
        fhir_path = Path(os.path.join(
            dirname, 
            'mimic-iv-clinical-database-demo-on-fhir-2.0/mimic-fhir'
        ))
    else:
        fhir_path = Path(fhir_path)
    
    pathlist = list(fhir_path.glob('*.ndjson'))
    forward_graph = defaultdict(set)
    reverse_graph = defaultdict(set)
    resources_map = defaultdict(lambda: defaultdict(dict))
    
    for file_path in pathlist:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first line to determine resource type
            first_line = f.readline()
            if not first_line:
                continue
            
            first_resource = json.loads(first_line)
            resource_name = first_resource.get('resourceType', 'Unknown')
            
            if resource_name not in resources_map:
                resources_map[resource_name] = defaultdict(dict)
            
            print(f"Processing: {resource_name}")
            
            # Process first resource
            resource = first_resource
            resource_id = f"{resource_name}/{resource.get('id', '')}"
            resources_map[resource_name][resource_id] = resource
            
            references = find_references(resource)
            for ref in references:
                forward_graph[resource_id].add(ref)
            for ref in references:
                reverse_graph[ref].add(resource_id)
            
            # Process remaining resources
            for line in f:
                resource = json.loads(line)
                resource_id = f"{resource_name}/{resource.get('id', '')}"
                resources_map[resource_name][resource_id] = resource
                
                references = find_references(resource)
                for ref in references:
                    forward_graph[resource_id].add(ref)
                for ref in references:
                    reverse_graph[ref].add(resource_id)
    
    print(f"\nGraphs built successfully!")
    print(f"Resource types: {list(resources_map.keys())}")
    print(f"Total resources: {sum(len(v) for v in resources_map.values())}")
    
    return forward_graph, reverse_graph, resources_map


def build_bundle_graph(bundle_dir):
    bundle_dir = Path(bundle_dir)
    forward_graph = defaultdict(set)
    reverse_graph = defaultdict(set)
    resources_map = {}
    
    for bundle_file in bundle_dir.glob("*.json"):
        with open(bundle_file, 'r', encoding='utf-8') as f:
            bundle = json.load(f)
        
        # Process all entries in the bundle
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")
            
            if not resource_type or not resource_id:
                continue
            
            full_id = f"{resource_type}/{resource_id}"
            resources_map[full_id] = resource
            
            # Find all references from this resource
            references = find_references(resource)
            for ref in references:
                forward_graph[full_id].add(ref)
                reverse_graph[ref].add(full_id)
    
    return forward_graph, reverse_graph, resources_map
