import random
from pathlib import Path


def split_patients_by_set(patient_ids, train_ratio=0.6, val_ratio=0.2, seed=None):
    """
    Split patients into train, validation, and test sets.
    
    Args:
        patient_ids: List of patient IDs to split
        train_ratio: Proportion for training set (default 0.6)
        val_ratio: Proportion for validation set (default 0.2)
        seed: Random seed for reproducibility
    
    Returns:
        Dictionary with 'train', 'validation', 'test' keys containing patient IDs
    """
    rng = random.Random(seed)
    patient_list = list(patient_ids)
    rng.shuffle(patient_list)
    
    total = len(patient_list)
    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)
    
    return {
        'train': set(patient_list[:train_count]),
        'validation': set(patient_list[train_count:train_count + val_count]),
        'test': set(patient_list[train_count + val_count:])
    }


def get_output_dir_for_split(base_dir, split_set, location_name=None):
    """
    Get the output directory for a specific split and location.
    
    Args:
        base_dir: Base output directory (e.g., 'location')
        split_set: Split set name ('train', 'validation', 'test')
        location_name: Optional location name (e.g., 'hospital_A', 'hospital_B')
    
    Returns:
        Path object for the output directory
    """
    if location_name:
        return Path(base_dir) / split_set / location_name
    else:
        return Path(base_dir) / split_set


def build_patient_bundle(patient_id, reverse_graph, forward_graph, resources_map):
    bundle_resources = set()
    bundle_resources.add(patient_id)  # Add the patient itself
    
    # Get all direct references to this patient
    direct_refs = reverse_graph.get(patient_id, set())
    bundle_resources.update(direct_refs)
    
    # For each direct reference, get their forward references (indirect refs)
    for ref_id in direct_refs:
        indirect_refs = forward_graph.get(ref_id, set())
        bundle_resources.update(indirect_refs)
    
    return bundle_resources


def get_patient_encounters(patient_id, reverse_graph):
    encounters = []
    for ref_id in reverse_graph.get(patient_id, set()):
        if ref_id.startswith('Encounter/'):
            encounters.append(ref_id)
    return encounters


def build_bundle_structure(resource_ids, resources_map):
    bundle_data = {
        'resources': resource_ids,
        'resource_objects': []
    }
    
    for resource_id in resource_ids:
        resource_type = resource_id.split('/')[0]
        if resource_type in resources_map and resource_id in resources_map[resource_type]:
            bundle_data['resource_objects'].append(
                resources_map[resource_type][resource_id]
            )
    
    return bundle_data


def build_split_dataset(strategy, resources_map, reverse_graph, forward_graph, seed=None):
    rng = random.Random(seed) if seed is not None else random.Random()
    
    # Get all encounters for each patient
    patient_encounters = {}
    for patient_id in resources_map['Patient'].keys():
        patient_encounters[patient_id] = get_patient_encounters(patient_id, reverse_graph)
    
    # Build bundles for all patients with split
    patient_bundles_a = {}
    patient_bundles_b = {}
    
    for patient_id in resources_map['Patient'].keys():
        # Get all resources for this patient
        all_resources = build_patient_bundle(patient_id, reverse_graph, forward_graph, resources_map)
        
        encounters = patient_encounters[patient_id]
        
        # Use strategy to split encounters
        encounters_a, encounters_b = strategy(
            encounters,
            patient_id,
            resources_map,
            rng
        )
        
        # Collect resources for hospital_B encounters
        hospital_b_resources = {patient_id}  # Always include patient
        
        for encounter_id in encounters_b:
            hospital_b_resources.add(encounter_id)
            # Add all resources that reference this encounter
            resources_ref_encounter = reverse_graph.get(encounter_id, set())
            hospital_b_resources.update(resources_ref_encounter)
            # Add forward references from those resources
            for resource_id in resources_ref_encounter:
                hospital_b_resources.update(forward_graph.get(resource_id, set()))
        
        # Hospital A gets all resources except those in hospital_B
        hospital_a_resources = all_resources - (hospital_b_resources - {patient_id})
        
        # Build bundle structures
        patient_bundles_a[patient_id] = build_bundle_structure(hospital_a_resources, resources_map)
        
        # Only create hospital_B bundle if there are encounters to split
        if len(encounters_b) > 0:
            patient_bundles_b[patient_id] = build_bundle_structure(hospital_b_resources, resources_map)
    
    return patient_bundles_a, patient_bundles_b


def build_split_dataset_with_sets(strategy, resources_map, reverse_graph, forward_graph, 
                                   train_ratio=0.6, val_ratio=0.2, seed=None):
    # Split patients into sets
    all_patient_ids = list(resources_map['Patient'].keys())
    patient_sets = split_patients_by_set(all_patient_ids, train_ratio, val_ratio, seed)
    
    # Build results structure
    results = {
        'train': {'hospital_a': {}, 'hospital_b': {}},
        'validation': {'hospital_a': {}, 'hospital_b': {}},
        'test': {'hospital_a': {}, 'hospital_b': {}}
    }
    
    # Process each split
    for split_name, patient_ids_in_split in patient_sets.items():
        # Filter resources for this split
        filtered_resources = {}
        for resource_type, resources in resources_map.items():
            filtered_resources[resource_type] = {}
            if resource_type == 'Patient':
                for patient_id, resource in resources.items():
                    if patient_id in patient_ids_in_split:
                        filtered_resources[resource_type][patient_id] = resource
            else:
                filtered_resources[resource_type] = resources
        
        # Build split dataset for this set
        bundles_a, bundles_b = build_split_dataset(
            strategy, 
            filtered_resources, 
            reverse_graph, 
            forward_graph, 
            seed
        )
        
        # Organize by hospital location
        results[split_name]['hospital_a'] = bundles_a
        results[split_name]['hospital_b'] = bundles_b
    
    return results
