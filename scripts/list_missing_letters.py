import os
import json

def list_missing_letters():
    """List all reports that don't have letters extracted."""
    outputs_dir = "config/outputs"
    missing = []
    
    for company_dir in os.listdir(outputs_dir):
        company_path = os.path.join(outputs_dir, company_dir)
        if not os.path.isdir(company_path):
            continue
            
        for year_dir in os.listdir(company_path):
            year_path = os.path.join(company_path, year_dir)
            if not os.path.isdir(year_path):
                continue
            
            # Check sections_metadata.json
            metadata_path = os.path.join(year_path, "sections", "sections_metadata.json")
            if not os.path.exists(metadata_path):
                continue
            
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check if letter exists
                has_letter = any(
                    s.get('section_type') == 'letter_to_stakeholders'
                    for s in metadata.get('sections', [])
                )
                
                if not has_letter:
                    missing.append({
                        'company': company_dir,
                        'year': year_dir
                    })
            except Exception as e:
                print(f"Error reading {metadata_path}: {e}")
    
    # Sort by company and year
    missing.sort(key=lambda x: (x['company'], x['year']))
    
    print(f"\n{'='*80}")
    print(f"Reports WITHOUT letters: {len(missing)}")
    print(f"{'='*80}\n")
    
    for item in missing:
        print(f"{item['company']:60} / {item['year']}")
    
    return missing

if __name__ == "__main__":
    list_missing_letters()
