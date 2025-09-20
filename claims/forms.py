from django import forms

class ClaimUploadForm(forms.Form):
    file = forms.FileField(
        label="Upload Claims CSV",
        help_text="Upload a CSV file with claims data"
    )

class RuleUploadForm(forms.Form):
    RULE_CHOICES = [
        ("TECHNICAL", "Technical"),
        ("MEDICAL", "Medical"),
    ]
    rule_type = forms.ChoiceField(choices=RULE_CHOICES)
    file = forms.FileField(
        label="Upload Rules File",
        help_text="Upload Technical or Medical rules (PDF or JSON)"
    )
