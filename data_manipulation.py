import json
import string
import pandas as pd
import numpy as np

from gecko import mutator
from pathlib import Path

def mutate_patients(bundle_location):
    rng = np.random.default_rng(8080)
    bundle_dir = Path(bundle_location)
    mutated_dir = bundle_dir.parent / "mutated"
    mutated_dir.mkdir(exist_ok=True)
    
    # Create grouped mutator with equal probability (25% each)
    grouped_mutator = mutator.with_group([
        mutator.with_insert(charset=string.ascii_lowercase, rng=rng),
        mutator.with_delete(rng=rng),
        mutator.with_substitute(charset=string.ascii_lowercase, rng=rng),
        mutator.with_transpose(rng=rng)
    ], rng=rng)
    
    for bundle_file in bundle_dir.glob("*.json"):
        with open(bundle_file, 'r', encoding='utf-8') as f:
            bundle = json.load(f)
        
        data = extract_patient_data(bundle_file)
        df = pd.DataFrame([data])
        
        mutations = []
        if df["name"].iloc[0]:
            mutations.append(("name", [(1, grouped_mutator)]))
        if df["birth_date"].iloc[0]:
            mutations.append(("birth_date", [(1, grouped_mutator)]))
        if df["deceased_date"].iloc[0]:
            mutations.append(("deceased_date", [(1, grouped_mutator)]))
        
        if mutations:
            df_mutated = mutator.mutate_data_frame(df, mutations)
        else:
            df_mutated = df
        
        patient_resource = bundle.get("entry", [])[0].get("resource", {})
        patient_resource["name"][0]["family"] = df_mutated["name"].iloc[0]
        patient_resource["birthDate"] = df_mutated["birth_date"].iloc[0]
        patient_resource["deceasedDateTime"] = df_mutated["deceased_date"].iloc[0]
        
        # Save mutated bundle
        mutated_file = mutated_dir / bundle_file.name
        with open(mutated_file, 'w', encoding='utf-8') as f:
            json.dump(bundle, f, indent=2)
        
        print(f"Mutated: {bundle_file.name} -> {mutated_file}")


def extract_patient_data(bundle_file):
     with open(bundle_file, 'r', encoding='utf-8') as f:
        bundle = json.load(f)
        patient_resource = bundle.get("entry", [])[0].get("resource", {})
        return {
            "name": patient_resource.get("name", [{}])[0].get("family", ""),
            "birth_date": patient_resource.get("birthDate", ""),
            "deceased_date": patient_resource.get("deceasedDateTime", "")
            }


mutate_patients("input/location/hospital_B")