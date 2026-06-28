import json
import random
from pathlib import Path
from graph_builder import build_bundle_graph


def extract_patient_record(patient_id, resources_map, reverse_graph):
    """Extract all relevant data for a patient."""
    patient = resources_map.get(patient_id, {})
    
    # Basic patient info
    name = patient.get("name", [{}])[0].get("family", "")
    birth_date = patient.get("birthDate", "")
    deceased = patient.get("deceasedDateTime", "")
    
    # Get all resources that reference this patient
    related_resources = reverse_graph.get(patient_id, set())
    
    # Extract conditions
    conditions = []
    for resource_id in related_resources:
        resource = resources_map.get(resource_id, {})
        if resource.get("resourceType") == "Condition":
            display = resource.get("code", {}).get("coding", [{}])[0].get("display", "")
            encounter_ref = resource.get("encounter", {}).get("reference", "")
            
            # Get encounter end date
            encounter = resources_map.get(encounter_ref, {})
            end_date = encounter.get("period", {}).get("end", "")
            
            if display:
                conditions.append(f"has {display} on date {end_date}")
    
    conditions_text = " and ".join(conditions) if conditions else ""
    
    # Extract medication requests
    medications = []
    for resource_id in related_resources:
        resource = resources_map.get(resource_id, {})
        if resource.get("resourceType") == "MedicationRequest":
            start_date = resource.get("dispenseRequest", {}).get("validityPeriod", {}).get("start", "")
            dosage_text = resource.get("dosageInstruction", [{}])[0].get("text", "") if resource.get("dosageInstruction") else ""
            
            # Get medication name
            med_ref = resource.get("medicationReference", {}).get("reference", "")
            medication = resources_map.get(med_ref, {})
            med_name = ""
            for identifier in medication.get("identifier", []):
                if "medication-name" in identifier.get("system", ""):
                    med_name = identifier.get("value", "")
                    break
            
            if not med_name:
                # Try code display as fallback
                med_name = medication.get("code", {}).get("coding", [{}])[0].get("display", "")
            
            if start_date or dosage_text or med_name:
                medications.append(f"on {start_date} {dosage_text} {med_name}".strip())
    
    medications_text = " and ".join(medications) if medications else ""
    
    # Extract observations
    observations = []
    for resource_id in related_resources:
        resource = resources_map.get(resource_id, {})
        if resource.get("resourceType") == "Observation":
            display = resource.get("code", {}).get("coding", [{}])[0].get("display", "")
            value = resource.get("valueQuantity", {}).get("value", "")
            unit = resource.get("valueQuantity", {}).get("unit", "")
            issued = resource.get("issued", "")
            
            if display and (value or unit):
                observations.append(f"{display} is {value} {unit} on {issued}".strip())
    
    observations_text = " and ".join(observations) if observations else ""
    
    return {
        "name": name,
        "birthDate": birth_date,
        "deceased": deceased,
        "conditions": conditions_text,
        "medications": medications_text,
        "observations": observations_text
    }


def format_record(record):
    """Format a record as COL VAL pairs."""
    parts = []
    for col_name, value in record.items():
        parts.append(f"COL {col_name} VAL {value}")
    return " ".join(parts)


def generate_matching_dataset(hospital_a_dir, hospital_b_dir, output_file):
    forward_a, reverse_a, resources_a = build_bundle_graph(hospital_a_dir)
    forward_b, reverse_b, resources_b = build_bundle_graph(hospital_b_dir)
    
    # Get all patient IDs
    patients_a = sorted([rid for rid in resources_a.keys() if rid.startswith("Patient/")])
    patients_b = sorted([rid for rid in resources_b.keys() if rid.startswith("Patient/")])
    
    print(f"Found {len(patients_a)} patients in hospital A")
    print(f"Found {len(patients_b)} patients in hospital B")
    
    dataset_lines = []
    
    print("Generating positive examples...")
    positive_count = 0
    for patient_id in patients_a:
        if patient_id in resources_b:
            record_a = extract_patient_record(patient_id, resources_a, reverse_a)
            record_b = extract_patient_record(patient_id, resources_b, reverse_b)
            
            formatted_a = format_record(record_a)
            formatted_b = format_record(record_b)
            
            dataset_lines.append(f"{formatted_a}\t\t{formatted_b}\t\t1")
            positive_count += 1
    
    print(f"Generated {positive_count} positive examples")
    
    print("Generating negative examples...")
    negative_count = 0
    for patient_b in patients_b:
        record_b = extract_patient_record(patient_b, resources_b, reverse_b)
        formatted_b = format_record(record_b)
        
        for patient_a in patients_a:
            if patient_a != patient_b:  # Skip the real match
                record_a = extract_patient_record(patient_a, resources_a, reverse_a)
                formatted_a = format_record(record_a)
                
                dataset_lines.append(f"{formatted_a}\t\t{formatted_b}\t\t0")
                negative_count += 1
    
    print(f"Generated {negative_count} negative examples")
    
    # Shuffle and write to file
    random.shuffle(dataset_lines)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in dataset_lines:
            f.write(line + "\n")
    
    print(f"Dataset written to {output_path}")
    print(f"Total examples: {len(dataset_lines)} ({positive_count} positive, {negative_count} negative)")