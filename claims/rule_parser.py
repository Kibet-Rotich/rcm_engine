import fitz
import re
import json


def parse_pdf_rules(filepath, rule_type="TECHNICAL"):
    """Extract rules from Technical or Medical PDF into JSON."""
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text("text")

    rules = {"type": rule_type, "rules": []}

    if rule_type == "TECHNICAL":
        # Services requiring prior approval
        matches = re.findall(r"(SRV\d+)\s+(.+?)\s+(YES|NO)", text)
        for srv, desc, req in matches:
            rules["rules"].append({
                "id": f"{srv}_APPROVAL",
                "rule_type": "service_approval",
                "service_code": srv,
                "description": desc.strip(),
                "requires_approval": (req == "YES"),
            })

        # Diagnosis requiring approval
        matches = re.findall(r"([A-Z]\d+\.\d+)\s+(.+?)\s+(YES|NO)", text)
        for dx, desc, req in matches:
            rules["rules"].append({
                "id": f"{dx}_APPROVAL",
                "rule_type": "diagnosis_approval",
                "diagnosis_code": dx,
                "description": desc.strip(),
                "requires_approval": (req == "YES"),
            })

        # Paid amount threshold
        amt_match = re.search(r"paid_amount_aed > AED (\d+)", text)
        if amt_match:
            rules["rules"].append({
                "id": "AMOUNT_THRESHOLD",
                "rule_type": "amount_threshold",
                "max_amount": int(amt_match.group(1)),
            })

        # ID formatting
        rules["rules"].append({
            "id": "ID_FORMATTING",
            "rule_type": "id_formatting",
            "requirements": [
                "All IDs must be uppercase alphanumeric",
                "unique_id structure: first4(National ID) – middle4(Member ID) – last4(Facility ID)",
                "Segments must be hyphen-separated"
            ],
        })

    elif rule_type == "MEDICAL":
        # Encounter restrictions
        if "Inpatient-only services" in text:
            rules["rules"].append({
                "id": "INPATIENT_SERVICES",
                "rule_type": "encounter_restriction",
                "encounter": "inpatient",
                "services": re.findall(r"SRV\d+", text.split("Outpatient-only")[0]),
            })
        if "Outpatient-only services" in text:
            rules["rules"].append({
                "id": "OUTPATIENT_SERVICES",
                "rule_type": "encounter_restriction",
                "encounter": "outpatient",
                "services": re.findall(r"SRV\d+", text.split("Outpatient-only")[1]),
            })

        # Facility restrictions
        if "Facility Registry" in text:
            facility_lines = re.findall(r"([A-Z0-9]{8})\s+([A-Z_]+)", text)
            facilities = {fid: ftype for fid, ftype in facility_lines}
            rules["rules"].append({
                "id": "FACILITY_RESTRICTIONS",
                "rule_type": "facility_restriction",
                "facilities": facilities,
            })

        # Diagnosis-service mappings
        diag_service = re.findall(r"([A-Z]\d+\.\d+).+?:\s+(SRV\d+)", text)
        for dx, srv in diag_service:
            rules["rules"].append({
                "id": f"{dx}_SERVICE_MAP",
                "rule_type": "diagnosis_service",
                "diagnosis_code": dx,
                "required_service": srv,
            })

        # Mutually exclusive diagnoses
        excl = re.findall(r"([A-Z]\d+\.\d+).+?cannot coexist with\s+([A-Z]\d+\.\d+)", text)
        for dx1, dx2 in excl:
            rules["rules"].append({
                "id": f"{dx1}_{dx2}_EXCLUSION",
                "rule_type": "mutually_exclusive",
                "diagnoses": [dx1, dx2],
            })

    return rules
