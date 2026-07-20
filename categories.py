"""Risk category definitions.

Each category has:
  - keywords:          phrases that make a segment a CANDIDATE (cheap, high recall)
  - exclude_keywords:  phrases that, if ALSO present, suppress the candidate
                        (cheap way to kill the "malware/jailbreak clause matched
                        AI-training category" kind of false positive before it
                        ever reaches the LLM)
  - verification_question: what we actually ask the LLM to confirm
  - severity: 2=critical, 1=high, 0=medium (drives sort order + score weight)
"""

SEVERITY_LABELS = {
    "critical": ("Critical", "#dc3545"),
    "high":     ("High",     "#fd7e14"),
    "medium":   ("Medium",   "#ffc107"),
    "low":      ("Low",      "#28a745"),
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SEVERITY_MAP = {2: "critical", 1: "high", 0: "medium"}

RISK_CATEGORIES: dict[str, dict] = {

    "mandatory_arbitration": {
        "label": "Mandatory Arbitration", "icon": "⚖️", "weight": 10, "severity": 2,
        "impact_statement": "Disputes must go through private arbitration instead of court.",
        "verification_question": "Does this text require the user to resolve disputes through binding arbitration instead of a court proceeding?",
        "interpretation": "This agreement requires you to resolve disputes through private arbitration rather than the court system.",
        "suggested_action": "Look for an opt-out window (commonly 30 days) and exercise it in writing if you want to preserve your right to sue.",
        "keywords": ["binding arbitration", "mandatory arbitration", "compel arbitration"],
        "exclude_keywords": [],
    },
    "class_action_waiver": {
        "label": "Class Action Waiver", "icon": "🙅", "weight": 9, "severity": 2,
        "impact_statement": "You may not join or bring a group lawsuit, even with other affected users.",
        "verification_question": "Does this text explicitly waive or prohibit the user's right to participate in a class action or collective lawsuit?",
        "interpretation": "You give up the right to bring or join a group lawsuit. Disputes must be pursued individually.",
        "suggested_action": "Some jurisdictions limit the enforceability of class action waivers — worth checking for your region.",
        "keywords": ["class action waiver", "waive class action", "individual proceeding only"],
        "exclude_keywords": [],
    },
    "liability_limitation": {
        "label": "Liability Cap / Limitation", "icon": "🧱", "weight": 9, "severity": 2,
        "impact_statement": "The company's financial responsibility for harming you is capped or excluded.",
        "verification_question": "Does this text limit or exclude the company's liability for damages arising from the service?",
        "interpretation": "The agreement limits how much the company can be held financially responsible for.",
        "suggested_action": "Weigh this against how critical the service is to you or your business.",
        "keywords": ["limit our liability", "liability shall not exceed", "consequential damages excluded"],
        "exclude_keywords": [],
    },
    "broad_ip_license": {
        "label": "Broad Content License Grant", "icon": "🔑", "weight": 8, "severity": 2,
        "impact_statement": "You grant the company broad rights to use and reproduce your uploaded content.",
        "verification_question": "Does this text grant the company broad, ongoing rights over content the user uploads or submits?",
        "interpretation": "You keep ownership of your content but grant the company a broad license, which may include commercial use.",
        "suggested_action": "Check if the license is limited to operating the service, or extends further (resale, sublicensing, marketing use).",
        "keywords": ["perpetual irrevocable license", "royalty-free license to use", "sublicense your content"],
        "exclude_keywords": [],
    },
    "ai_training_permission": {
        "label": "AI / ML Training Use of Your Content", "icon": "🧠", "weight": 6, "severity": 1,
        "impact_statement": "Your content or data may be used to train the company's AI/ML models.",
        "verification_question": "Does this text state that content YOU submit or upload may be used to train, develop, or improve the company's AI or machine learning models? Answer NO if the text is instead about security, abuse prevention, or the company's own AI being used to serve you a feature — that is not the same thing.",
        "interpretation": "Content you contribute may be used to train or improve the company's models.",
        "suggested_action": "Check account/privacy settings for an AI-training opt-out before uploading original or sensitive content.",
        "keywords": ["train our ai", "used to train", "improve our machine learning", "model training data", "develop machine learning models"],
        # Suppresses false positives like abuse/security clauses that merely mention adjacent AI vocabulary
        "exclude_keywords": ["malware", "hacking", "jailbreaking", "phishing", "denial of service"],
    },
    "data_selling_sharing": {
        "label": "Data Selling or Third-Party Sharing", "icon": "📤", "weight": 6, "severity": 1,
        "impact_statement": "Your personal data may be shared with, or sold to, third parties.",
        "verification_question": "Does this text allow the company to sell user data to third parties, or share it beyond what's needed to run the service?",
        "interpretation": "The agreement permits sharing or monetizing personal data with outside parties.",
        "suggested_action": "Check privacy settings for opt-outs; many regions grant a 'Do Not Sell My Data' right.",
        "keywords": ["sell your information", "sold to third parties", "share with our partners", "business partners and affiliates"],
        "exclude_keywords": [],
    },
    "auto_renewal": {
        "label": "Auto-Renewal Clause", "icon": "🔄", "weight": 5, "severity": 1,
        "impact_statement": "Your subscription may renew automatically unless you cancel.",
        "verification_question": "Does this text state that a subscription or agreement renews automatically unless the user cancels?",
        "interpretation": "The agreement continues for further periods unless you actively cancel before renewal.",
        "suggested_action": "Note the renewal date and set a reminder a week ahead.",
        "keywords": ["auto-renew", "automatically renew", "recurring billing"],
        "exclude_keywords": [],
    },
    "termination_suspension": {
        "label": "Termination and Suspension Rights", "icon": "🚪", "weight": 4, "severity": 1,
        "impact_statement": "The provider can suspend or terminate your account access at its discretion.",
        "verification_question": "Does this text give the provider broad discretion to terminate or suspend the user's account?",
        "interpretation": "The provider reserves the right to end your access, possibly without prior notice.",
        "suggested_action": "Keep regular backups/exports of anything important stored on the platform.",
        "keywords": ["terminate your account", "suspend your access", "at our sole discretion"],
        "exclude_keywords": [],
    },
    "unilateral_modification": {
        "label": "Unilateral Terms Modification", "icon": "✏️", "weight": 4, "severity": 0,
        "impact_statement": "The company can change the agreement's terms without your active consent.",
        "verification_question": "Does this text allow the provider to modify the agreement's terms without requiring the user's explicit consent?",
        "interpretation": "The provider can amend these terms; continued use after the change may count as acceptance.",
        "suggested_action": "Note how the provider says it will notify you of changes (email, in-app, posted date) and check periodically.",
        "keywords": ["change these terms", "modify these terms at any time", "terms may be updated"],
        "exclude_keywords": [],
    },
    "governing_law_jurisdiction": {
        "label": "Governing Law / Jurisdiction", "icon": "🌍", "weight": 3, "severity": 0,
        "impact_statement": "Disputes are governed by a specific jurisdiction's laws.",
        "verification_question": "Does this text specify which jurisdiction's laws or courts govern disputes under the agreement? Answer NO if the text only describes where the company is legally incorporated, without addressing dispute resolution.",
        "interpretation": "The agreement specifies which jurisdiction's laws or courts apply to disputes.",
        "suggested_action": "Check whether that jurisdiction offers strong consumer protections relevant to your situation.",
        "keywords": ["governing law", "exclusive jurisdiction of the courts", "laws of the state of"],
        "exclude_keywords": [],
    },
    "warranty_disclaimer": {
        "label": "Warranty Disclaimer", "icon": "⚠️", "weight": 3, "severity": 0,
        "impact_statement": "The service is provided without guarantees of quality or fitness for a purpose.",
        "verification_question": "Does this text broadly disclaim warranties about the service's performance, accuracy, or reliability?",
        "interpretation": "The provider disclaims warranties about the service to the extent the law allows.",
        "suggested_action": "Avoid relying on an 'as is' service for anything critical without a backup plan.",
        "keywords": ["provided as is", "without warranty of any kind", "as available basis"],
        "exclude_keywords": [],
    },
    "data_retention": {
        "label": "Data Retention After Account Closure", "icon": "🗄️", "weight": 3, "severity": 0,
        "impact_statement": "Your data may be kept even after you close your account.",
        "verification_question": "Does this text describe retaining user data for some period after the user deletes or closes their account?",
        "interpretation": "The company retains some data after account closure for legal or operational reasons.",
        "suggested_action": "Use the platform's data deletion tools proactively rather than assuming closure erases everything.",
        "keywords": ["retain your data after", "retained for legal purposes", "keep data following account closure"],
        "exclude_keywords": [],
    },
    "indemnification": {
        "label": "Indemnification Obligation", "icon": "💰", "weight": 5, "severity": 1,
        "impact_statement": "You may have to cover the company's legal costs from claims related to your use.",
        "verification_question": "Does this text require the user to indemnify (compensate) the company for legal costs or losses from a third-party claim?",
        "interpretation": "You agree to cover the company's legal costs if a third party brings a claim tied to your use of the service.",
        "suggested_action": "Check whether the obligation is mutual, or one-sided in the company's favor.",
        "keywords": ["indemnify and hold harmless", "you agree to indemnify"],
        "exclude_keywords": [],
    },
    "no_refund_policy": {
        "label": "Non-Refundable Payments", "icon": "❌", "weight": 2, "severity": 0,
        "impact_statement": "Payments may not be refundable, even if you're unsatisfied.",
        "verification_question": "Does this text state that payments are non-refundable?",
        "interpretation": "The agreement states payments are non-refundable.",
        "suggested_action": "Check your jurisdiction's cooling-off / refund rights before paying.",
        "keywords": ["non-refundable", "all sales are final", "no refunds will be issued"],
        "exclude_keywords": [],
    },
}
