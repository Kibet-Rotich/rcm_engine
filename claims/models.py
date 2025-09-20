from django.db import models


class Claim(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("VALIDATED", "Validated"),
        ("NOT_VALIDATED", "Not Validated"),
    ]

    ERROR_CHOICES = [
        ("NONE", "No Error"),
        ("TECHNICAL", "Technical Error"),
        ("MEDICAL", "Medical Error"),
        ("BOTH", "Both Errors"),
    ]

    claim_id = models.CharField(max_length=50, unique=True)
    encounter_type = models.CharField(max_length=50, blank=True, null=True)
    service_date = models.DateField(blank=True, null=True)
    national_id = models.CharField(max_length=50)
    member_id = models.CharField(max_length=50)
    facility_id = models.CharField(max_length=50)
    unique_id = models.CharField(max_length=50, blank=True, null=True)

    # Comma-separated diagnosis codes for SQLite
    diagnosis_codes = models.TextField(blank=True, null=True)

    service_code = models.CharField(max_length=50)
    paid_amount_aed = models.DecimalField(max_digits=10, decimal_places=2)
    approval_number = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING"
    )
    error_type = models.CharField(
        max_length=20, choices=ERROR_CHOICES, default="NONE"
    )
    error_explanation = models.TextField(blank=True, null=True)
    recommended_action = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Claim {self.claim_id} - {self.status}"

    def diagnosis_list(self):
        """Convert comma-separated diagnosis codes into list."""
        if self.diagnosis_codes:
            return [code.strip() for code in self.diagnosis_codes.split(",")]
        return []


class Rule(models.Model):
    RULE_TYPES = [
        ("TECHNICAL", "Technical"),
        ("MEDICAL", "Medical"),
    ]

    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    tenant_id = models.CharField(max_length=50, default="default")  # multi-tenant support

    # Store parsed rules as JSON string (text field for SQLite)
    parsed_json = models.TextField()

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rule_type} Rule - {self.name}"
