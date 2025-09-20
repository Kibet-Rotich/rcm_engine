from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def index(request):
    return render(request, "index.html")

import csv
import uuid
from datetime import datetime
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from .models import Claim

@login_required
def upload_claims(request):
    if request.method == "POST" and request.FILES.get("file"):
        csv_file = request.FILES["file"]
        fs = FileSystemStorage()
        filename = fs.save(csv_file.name, csv_file)
        filepath = fs.path(filename)

        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # --- Parse service_date ---
                raw_date = row.get("service_date")
                parsed_date = None
                if raw_date:
                    try:
                        parsed_date = datetime.strptime(raw_date, "%m/%d/%y").date()
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(raw_date, "%d/%m/%y").date()
                        except ValueError:
                            parsed_date = None  # leave empty if not parseable

                # --- Create claim ---
                Claim.objects.create(
                    claim_id=str(uuid.uuid4())[:8],
                    encounter_type=row.get("encounter_type"),
                    service_date=parsed_date,
                    national_id=row.get("national_id"),
                    member_id=row.get("member_id"),
                    facility_id=row.get("facility_id"),
                    unique_id=row.get("unique_id"),
                    diagnosis_codes=row.get("diagnosis_codes"),
                    service_code=row.get("service_code"),
                    paid_amount_aed=row.get("paid_amount_aed"),
                    approval_number=row.get("approval_number"),
                    status="PENDING",
                    error_type="NONE",
                )

        return redirect("claim_results")

    return render(request, "claims/upload_claims.html")


from .rule_parser import parse_pdf_rules
from .forms import RuleUploadForm
from .models import Rule

@login_required
def upload_rules(request):
    if request.method == "POST":
        form = RuleUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            rule_type = form.cleaned_data["rule_type"]

            if file.name.endswith(".json"):
                parsed = json.load(file)
            elif file.name.endswith(".pdf"):
                # Save to temp then parse
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    for chunk in file.chunks():
                        tmp.write(chunk)
                    tmp.flush()
                    parsed = parse_pdf_rules(tmp.name, rule_type)
            else:
                parsed = {"note": "Unsupported format"}

            Rule.objects.create(
                name=file.name,
                rule_type=rule_type,
                parsed_json=json.dumps(parsed),
            )
            messages.success(request, f"{rule_type} rules uploaded and parsed successfully!")
            return redirect("upload_rules")
    else:
        form = RuleUploadForm()
    return render(request, "claims/upload_rules.html", {"form": form})



from django.shortcuts import redirect
from django.contrib import messages
from .validators import validate_claims

@login_required
def run_validation(request):
    validate_claims()
    messages.success(request, "Validation completed successfully!")
    return redirect("upload_claims")


from django.shortcuts import render
from .models import Claim

@login_required
def claim_results(request):
    claims = Claim.objects.all().order_by("-created_at")
    return render(request, "claims/results.html", {"claims": claims})



from .models import Rule
import json

@login_required
def rule_summary(request):
    rules = Rule.objects.all().order_by("-uploaded_at")

    parsed_rules = []
    for r in rules:
        try:
            parsed = json.loads(r.parsed_json)
        except Exception:
            parsed = {"error": "Could not parse JSON"}
        parsed_rules.append({
            "name": r.name,
            "type": r.rule_type,
            "uploaded_at": r.uploaded_at,
            "parsed": parsed.get("rules", []),
        })

    return render(request, "claims/rule_summary.html", {"rules": parsed_rules})

from django.db.models import Count, Sum
from django.shortcuts import render
from .models import Claim

@login_required
def charts(request):
    from decimal import Decimal

    counts = Claim.objects.values("error_type").annotate(total=Count("id"))
    amounts = Claim.objects.values("error_type").annotate(total=Sum("paid_amount_aed"))

    error_categories = ["TECHNICAL", "MEDICAL", "BOTH", "NONE"]
    claim_counts = []
    paid_amounts = []

    for cat in error_categories:
        count = next((c["total"] for c in counts if c["error_type"] == cat), 0)
        amount = next((a["total"] for a in amounts if a["error_type"] == cat), 0)

        # Convert Decimal → float so JS understands
        if isinstance(amount, Decimal):
            amount = float(amount)

        claim_counts.append(count)
        paid_amounts.append(amount)

    context = {
        "error_categories": error_categories,
        "claim_counts": claim_counts,
        "paid_amounts": paid_amounts,
    }
    return render(request, "charts.html", context)

