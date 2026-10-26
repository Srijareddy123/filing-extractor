from filing_extractor.grounding import ground, is_grounded
from filing_extractor.rules import RulesExtractor
from filing_extractor.schema import UNRESOLVED, Extraction

R = RulesExtractor()


def test_grounding_demotes_invented_values() -> None:
    passage = "The facility is $500,000,000 and matures on March 1, 2030."
    e = Extraction(facility_size="$500,000,000", maturity="June 1, 2031", lender="Acme Bank")
    out = ground(e, passage)
    assert out.facility_size == "$500,000,000"
    assert out.maturity == UNRESOLVED
    assert out.lender == UNRESOLVED


def test_covenant_grounding_checks_both_parts() -> None:
    passage = "The Borrower shall not permit the Leverage Ratio to exceed 3.50 to 1.00."
    assert is_grounded("financial_covenants", "Leverage Ratio | 3.50 to 1.00", passage)
    assert not is_grounded("financial_covenants", "Leverage Ratio | 4.00 to 1.00", passage)


def test_rules_size_and_lender() -> None:
    text = (
        "CREDIT AGREEMENT among ACME CORP., as Borrower, and WELLS FARGO BANK, NATIONAL "
        "ASSOCIATION, as Administrative Agent, providing a revolving credit facility in "
        "an aggregate principal amount of $750,000,000."
    )
    out = R.extract(text)
    assert out.facility_size == "$750,000,000"
    assert out.lender == "WELLS FARGO BANK, NATIONAL ASSOCIATION"


def test_rules_rejects_sublimit_amount() -> None:
    text = "The Letter of Credit Sublimit means an amount equal to $75,000,000."
    assert R.extract(text).facility_size == UNRESOLVED


def test_rules_maturity() -> None:
    text = "“Maturity Date” means March 25, 2030, or any earlier date of termination."
    assert R.extract(text).maturity == "March 25, 2030"


def test_rules_margin_and_default_rate() -> None:
    assert (
        R.extract("Loans bear interest at Term SOFR plus 1.75% per annum.").interest_margin
        == "1.75%"
    )
    default = "Overdue amounts bear the Default Rate, the rate plus 2.00% per annum."
    assert R.extract(default).interest_margin == UNRESOLVED


def test_rules_covenant_and_basket() -> None:
    cov = "The Borrower shall not permit the Total Leverage Ratio to exceed 4.50 to 1.00."
    assert R.extract(cov).financial_covenants == "Total Leverage Ratio | 4.50 to 1.00"
    basket = "Investments are permitted if the Total Leverage Ratio does not exceed 2.50 to 1.00."
    assert R.extract(basket).financial_covenants == UNRESOLVED


def test_rules_boilerplate_is_all_unresolved() -> None:
    out = R.extract("Each notice shall be in writing and delivered by hand or by email.")
    assert all(v == UNRESOLVED for v in out.as_dict().values())
