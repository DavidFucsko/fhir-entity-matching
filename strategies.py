import random


def temporal_split(encounters, patient_id, resources_map, rng=None):
    # Split encounters by temporal order (chronological).
    # First half goes to hospital_A, second half to hospital_B.
    if len(encounters) <= 1:
        return set(encounters), set()
    
    dated = []
    for encounter_id in encounters:
        encounter = resources_map["Encounter"][encounter_id]
        start = encounter.get("period", {}).get("start")
        dated.append((encounter_id, start))
    
    # Sort by start date
    dated.sort(key=lambda x: x[1] or "")
    
    midpoint = len(dated) // 2
    encounters_a = {e for e, _ in dated[:midpoint]}
    encounters_b = {e for e, _ in dated[midpoint:]}
    
    return encounters_a, encounters_b


def service_type_split(encounters, patient_id, resources_map, rng=None):
    # Split encounters by service type (e.g., TRAUMA, SURGERY, MEDICAL).
    # Encounters with different service types are partitioned alphabetically.
    services = {}
    for encounter_id in encounters:
        encounter = resources_map["Encounter"][encounter_id]
        service = encounter.get("serviceType", {}).get("coding", [{}])[0].get("code")
        services[encounter_id] = service
    
    unique_services = sorted({s for s in services.values() if s is not None})
    
    # Fall back to temporal if only one service type
    if len(unique_services) < 2:
        print(f"Patient {patient_id} has only one service type; falling back to temporal split.")
        return temporal_split(encounters, patient_id, resources_map, rng)
    
    midpoint = len(unique_services) // 2
    group_a = set(unique_services[:midpoint])
    encounters_a = {eid for eid, svc in services.items() if svc in group_a}
    encounters_b = set(encounters) - encounters_a
    
    return encounters_a, encounters_b


def location_split(encounters, patient_id, resources_map, rng=None):
    # Split encounters by location.
    # Encounters at different locations are partitioned.
    encounter_locations = {}
    for encounter_id in encounters:
        encounter = resources_map["Encounter"][encounter_id]
        location_refs = []
        for loc in encounter.get("location", []):
            ref = loc.get("location", {}).get("reference")
            if ref:
                location_refs.append(ref)
        encounter_locations[encounter_id] = tuple(sorted(location_refs))
    
    unique_groups = list(set(encounter_locations.values()))
    
    # Fall back to temporal if only one location
    if len(unique_groups) < 2:
        print(f"Patient {patient_id} has only one location; falling back to temporal split.")
        return temporal_split(encounters, patient_id, resources_map, rng)
    
    midpoint = len(unique_groups) // 2
    group_a = set(unique_groups[:midpoint])
    encounters_a = {eid for eid, locs in encounter_locations.items() if locs in group_a}
    encounters_b = set(encounters) - encounters_a
    
    return encounters_a, encounters_b


def random_split(encounters, patient_id, resources_map, rng=None):
    # Randomly split encounters between two hospitals.
    # Useful for benchmarking; not recommended for real training.
    rng = rng or random.Random()
    encounters_list = list(encounters)
    
    if len(encounters_list) <= 1:
        return set(encounters_list), set()
    
    n = max(1, len(encounters_list) // 2)
    encounters_b = set(rng.sample(encounters_list, n))
    encounters_a = set(encounters_list) - encounters_b
    
    return encounters_a, encounters_b


def mixed_split(encounters, patient_id, resources_map, rng=None):
    # Randomly choose between temporal, service_type, and location splits.
    # - 50% temporal
    # - 25% service_type
    # - 25% location
    # Since service type is too sparse, we will use 70% temporal and 30% location for now.
    rng = rng or random.Random()
    r = rng.random()
    
    # if r < 0.50:
    #     return temporal_split(encounters, patient_id, resources_map, rng)
    # elif r < 0.75:
    #     return service_type_split(encounters, patient_id, resources_map, rng)
    # else:
    #     return location_split(encounters, patient_id, resources_map, rng)

    if r < 0.70:
        return temporal_split(encounters, patient_id, resources_map, rng)
    else:
        return location_split(encounters, patient_id, resources_map, rng)


# Registry of all available strategies
SPLIT_STRATEGIES = {
    "temporal": temporal_split,
    "service_type": service_type_split,
    "location": location_split,
    "random": random_split,
    "mixed": mixed_split,
}
