# Error analysis: rules on val + test

48 wrong (passage, field) pairs out of 830. By kind: false_answer 34, missed 11, boundary 2, wrong_value 1.

| Field | missed | false_answer | boundary | wrong_value |
|---|---|---|---|---|
| facility_size | 0 | 18 | 0 | 1 |
| maturity | 0 | 6 | 0 | 0 |
| interest_margin | 4 | 6 | 0 | 0 |
| lender | 3 | 1 | 2 | 0 |
| financial_covenants | 4 | 3 | 0 | 0 |

## Pattern 1: facility_size, false_answer (18 cases)

gold is unresolved, model gave a value.

- `fx0012` gold: `unresolved` | predicted: `$50,000,000`
  > 20 “ LC Commitment ” means, with respect to CoBank, as Issuing Bank, $50,000,000; provided that the LC Commitment shall be reduced by the amount of any Letters of Credit issued and outstanding under the second sentence of the definition of Letters of Credit. For the avoidance of doubt, any Lender that is an Issuing Bank pursuant to the second sentence of the definition of Issuing Bank shall not have any LC Commitment ...

- `fx0016` gold: `unresolved` | predicted: `$10,000,000`
  > (f) Voting Participants . Notwithstanding anything in this Section 8.07 to the contrary, any Farm Credit Lender that (i) is the owner of a participation in a Commitment (including Advances outstanding thereunder) initially in the aggregate amount of at least $10,000,000; (ii) is, by written notice to the Borrowers and the Administrative Agent (a “ Voting Participant Notification ”), designated by the selling Lender a ...

## Pattern 2: interest_margin, false_answer (6 cases)

gold is unresolved, model gave a value.

- `fx0032` gold: `unresolved` | predicted: `1.00%`
  > “ Base Rate ” means for any day a fluctuating rate per annum equal to the highest of (a) the Federal Funds Rate plus 1/2 of 1%, (b) the rate of interest in effect for such day as publicly announced from time to time by Bank of America as its “prime rate”, (c) Term SOFR plus 1.00% and (d) 1.00%. The “prime rate” is a rate set by Bank of America based upon various factors including Bank of America’s costs and desired r ...

- `fx0247` gold: `unresolved` | predicted: `0.25%`
  > (c) Fronting Fees . The Borrower agrees to pay directly to each LC Issuer, for its own account, a fee in respect of each Letter of Credit issued by it, payable on the date of issuance (or any increase in the amount, or renewal or extension) thereof, computed at the rate of 0.25% per annum on the Stated Amount thereof for the period from the date of issuance (or increase, renewal or extension) to the expiration date t ...

## Pattern 3: maturity, false_answer (6 cases)

gold is unresolved, model gave a value.

- `fx0057` gold: `unresolved` | predicted: `June 30, 2024`
  > FIFTH AMENDED AND RESTATED CREDIT AGREEMENT, Page 19 “ Interest Payment Date ” means, (a) as to any ABR Loan, the last Business Day of each March, June, September and December, and the Revolving Termination Date or Term Loan Termination Date, as applicable, of the facility under which such Loan was made, commencing June 30, 2024, (b) as to any Term Benchmark Loan having an Interest Period of three months or less, the ...

- `fx0140` gold: `unresolved` | predicted: `June 30, 2024`
  > [[6108061]] “ First Amendment Period ” means the period commencing on the First Amendment Effective Date and ending on the earlier to occur of the First Amendment Period Termination Date and the date on which the Parent shall have delivered to the Administrative Agent the financial statements as of and for the fiscal quarter of the Parent ending June 30, 2024 pursuant to Section 5.01(b), together with the related cer ...
