"""Generates a synthetic sample health insurance policy PDF for demo/testing."""
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

styles = getSampleStyleSheet()
doc = SimpleDocTemplate("data/sample_policy.pdf", pagesize=A4,
                         topMargin=2*cm, bottomMargin=2*cm)
story = []

def h(text): story.append(Paragraph(f"<b>{text}</b>", styles["Heading2"])); story.append(Spacer(1, 8))
def p(text): story.append(Paragraph(text, styles["Normal"])); story.append(Spacer(1, 8))

h("SecureHealth Family Floater Policy")
p("Policy Number: SH-2026-00123 &nbsp;&nbsp; Insurer: SecureHealth General Insurance Co. Ltd.")
p("Policy Type: Individual Health Insurance &nbsp;&nbsp; Sum Insured: Rs. 5,00,000")
p("This policy provides coverage for hospitalisation expenses, day care procedures, and pre/post "
  "hospitalisation expenses as detailed in this document, subject to the terms, conditions, "
  "exclusions and limits stated herein.")
story.append(PageBreak())

h("Hospitalisation Cover")
p("The Company shall indemnify Medical Expenses incurred for Hospitalisation of the Insured Person "
  "during the Policy Year, up to the Sum Insured, for treatment taken as an inpatient for more than "
  "24 consecutive hours in a Network or non-Network Hospital, provided the treatment is Medically "
  "Necessary. Covered procedures include, but are not limited to, knee replacement, hip replacement, "
  "cardiac surgery, cataract surgery and other surgical/medical procedures that are payable and admissible "
  "under this policy.")
p("Room Rent: Room, boarding and nursing expenses are covered up to 1% of the Sum Insured per day. "
  "ICU expenses are covered up to 2% of the Sum Insured per day. If the Insured Person opts for a room "
  "category with rent higher than eligible, the Company shall pay the proportionate deductions as per "
  "the applicable proportionate deduction clause.")
story.append(PageBreak())

h("Day Care Procedures")
p("The following procedures, among others, are covered even if the Hospitalisation is for less than "
  "24 hours, due to technological advancement: Cataract Surgery, Dialysis, Chemotherapy, Tonsillectomy, "
  "Lithotripsy (Kidney Stone Removal). These are payable and eligible under this policy subject to the "
  "co-payment and deductible mentioned below.")
story.append(PageBreak())

h("Waiting Period")
p("Initial waiting period: 30 days from the policy commencement date for all illnesses (except accidents). "
  "Pre-existing diseases waiting period: 36 months of continuous coverage from the first policy inception "
  "date, after which pre-existing conditions become payable.")
p("Specific illness waiting period: 24 months for conditions such as cataract, hernia, and joint "
  "replacement surgery (including knee replacement) unless necessitated by an accident.")
story.append(PageBreak())

h("Deductible and Co-payment")
p("Deductible: Rs. 5,000 is applicable per claim, over and above which the Company's liability begins. "
  "Co-payment: A mandatory Co-payment of 10% of each admissible claim amount shall be borne by the "
  "Insured Person for all claims, and an additional 10% Co-payment (total 20%) applies for Insured "
  "Persons aged 61 years and above at the time of Hospitalisation.")
story.append(PageBreak())

h("Exclusions")
p("The Company shall not be liable to make payment under this Policy in respect of any expenses "
  "incurred in connection with or in respect of the following, unless expressly stated to the contrary "
  "in this Policy:")
story.append(Paragraph(
    "- Cosmetic or plastic surgery unless necessitated due to an accident or as part of medically "
    "necessary treatment<br/>"
    "- Dental treatment, except arising from accidental bodily injury requiring hospitalisation<br/>"
    "- Treatment for infertility, sterilisation, and voluntary termination of pregnancy<br/>"
    "- Weight control services including surgery for obesity<br/>"
    "- Self-inflicted injury and treatment for substance abuse or alcoholism<br/>"
    "- War, invasion, act of foreign enemy, and nuclear/radiation contamination<br/>"
    "- Experimental or unproven treatment not recognised by modern medicine<br/>",
    styles["Normal"]))
story.append(Spacer(1, 8))
story.append(PageBreak())

h("Sub-limits")
p("Cataract Surgery: payable up to 25% of Sum Insured or Rs. 40,000 per eye, whichever is lower. "
  "Knee Replacement (unilateral): payable up to Rs. 1,50,000 per knee. Ambulance charges: payable up "
  "to Rs. 2,000 per Hospitalisation.")
story.append(PageBreak())

h("Claim Procedure and Conditions")
p("Cashless claims: The Insured Person must obtain pre-authorisation from the Company through the "
  "Network Hospital's insurance desk before planned Hospitalisation, or within 24 hours for emergency "
  "admissions. Reimbursement claims: All original bills, discharge summary, and investigation reports "
  "must be submitted within 30 days of discharge from the Hospital.")

doc.build(story)
print("Sample policy PDF generated.")
