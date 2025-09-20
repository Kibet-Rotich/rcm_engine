import json
from .models import Claim, Rule


def load_rules():
    """Return parsed technical + medical rules (JSON)."""
    rules = {"TECHNICAL": [], "MEDICAL": []}
    for rule in Rule.objects.all():
        try:
            parsed = json.loads(rule.parsed_json)
            rules[rule.rule_type].extend(parsed.get("rules", []))
        except Exception:
            continue
    return rules


def validate_claims():
    """Validate all pending claims against parsed rules."""
    rules = load_rules()
    tech_rules = rules.get("TECHNICAL", [])
    med_rules = rules.get("MEDICAL", [])

    for claim in Claim.objects.filter(status="PENDING"):
        errors = []
        error_types = set()

        dx = claim.diagnosis_list()
        sc = claim.service_code
        amount = float(claim.paid_amount_aed or 0)

        # --- TECHNICAL RULES ---
        for rule in tech_rules:
            rtype = rule.get("rule_type")

            if rtype == "service_approval":
                if sc == rule.get("service_code") and rule.get("requires_approval", False):
                    if not claim.approval_number:
                        errors.append(f"Service {sc} requires prior approval.")
                        error_types.add("TECHNICAL")

            elif rtype == "diagnosis_approval":
                for code in dx:
                    if code == rule.get("diagnosis_code") and rule.get("requires_approval", False):
                        if not claim.approval_number:
                            errors.append(f"Diagnosis {code} requires prior approval.")
                            error_types.add("TECHNICAL")

            elif rtype == "amount_threshold":
                if amount > rule.get("max_amount", 0):
                    if not claim.approval_number:
                        errors.append(f"Paid amount {amount} exceeds threshold {rule['max_amount']} AED.")
                        error_types.add("TECHNICAL")

            elif rtype == "id_formatting":
                if not claim.national_id.isalnum() or not claim.national_id.isupper():
                    errors.append("National ID must be uppercase alphanumeric.")
                    error_types.add("TECHNICAL")
                if claim.unique_id and "-" not in claim.unique_id:
                    errors.append("Unique ID format invalid (expected hyphen-separated).")
                    error_types.add("TECHNICAL")

        # --- MEDICAL RULES ---
        for rule in med_rules:
            rtype = rule.get("rule_type")

            if rtype == "encounter_restriction":
                if sc in rule.get("services", []):
                    expected = rule.get("encounter", "").lower()
                    if claim.encounter_type and claim.encounter_type.lower() != expected:
                        errors.append(f"Service {sc} only allowed for {expected} encounter.")
                        error_types.add("MEDICAL")

            elif rtype == "facility_restriction":
                facilities = rule.get("facilities", {})
                ftype = facilities.get(claim.facility_id)

                if ftype:
                    # Allowed services for this facility type
                    allowed_map = {
                        "MATERNITY_HOSPITAL": ["SRV2008"],
                        "DIALYSIS_CENTER": ["SRV1003", "SRV2010"],
                        "CARDIOLOGY_CENTER": ["SRV2001", "SRV2011"],
                        "GENERAL_HOSPITAL": [
                            "SRV1001", "SRV1002", "SRV1003",
                            "SRV2001", "SRV2002", "SRV2003",
                            "SRV2004", "SRV2006", "SRV2007",
                            "SRV2008", "SRV2010", "SRV2011"
                        ],
                    }

                    allowed_services = allowed_map.get(ftype, [])

                    if claim.service_code not in allowed_services:
                        errors.append(
                            f"Service {claim.service_code} not permitted for facility type {ftype} (Facility {claim.facility_id})."
                        )
                        error_types.add("MEDICAL")


            elif rtype == "diagnosis_service":
                for code in dx:
                    if code == rule.get("diagnosis_code") and sc != rule.get("required_service"):
                        errors.append(f"Diagnosis {code} requires {rule['required_service']}, not {sc}.")
                        error_types.add("MEDICAL")

            elif rtype == "mutually_exclusive":
                pair = rule.get("diagnoses", [])
                if all(p in dx for p in pair):
                    errors.append(f"Diagnoses {pair[0]} and {pair[1]} cannot coexist.")
                    error_types.add("MEDICAL")

        # --- Update Claim ---
        if errors:
            claim.status = "NOT_VALIDATED"
            if len(error_types) == 1:
                claim.error_type = error_types.pop()
            elif len(error_types) > 1:
                claim.error_type = "BOTH"
            claim.error_explanation = "\n".join(errors)
            claim.recommended_action = "Please review errors and resubmit with corrections."
        else:
            claim.status = "VALIDATED"
            claim.error_type = "NONE"
            claim.error_explanation = "No errors found."
            claim.recommended_action = "Proceed to payment."

        claim.save()
