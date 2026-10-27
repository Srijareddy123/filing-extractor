# Error analysis: lora on val + test

47 wrong (passage, field) pairs out of 830. By kind: false_answer 35, missed 7, wrong_value 3, boundary 2.

| Field | missed | false_answer | boundary | wrong_value |
|---|---|---|---|---|
| facility_size | 0 | 17 | 0 | 1 |
| maturity | 0 | 5 | 0 | 0 |
| interest_margin | 5 | 4 | 0 | 1 |
| lender | 2 | 7 | 2 | 1 |
| financial_covenants | 0 | 2 | 0 | 0 |

## Pattern 1: facility_size, false_answer (17 cases)

gold is unresolved, model gave a value.

- `fx0012` gold: `unresolved` | predicted: `$50,000,000`
  > 20 “ LC Commitment ” means, with respect to CoBank, as Issuing Bank, $50,000,000; provided that the LC Commitment shall be reduced by the amount of any Letters of Credit issued and outstanding under the second sentence of the definition of Letters of Credit. For the avoidance of doubt, any Lender that is an Issuing Bank pursuant to the second sentence of the definition of Issuing Bank shall not have any LC Commitment ...

- `fx0174` gold: `unresolved` | predicted: `$15,000,000`
  > 93 (s) Liens not otherwise permitted hereunder on assets other than the Collateral securing Indebtedness or other obligations in the aggregate principal amount not to exceed the greater of (i) $15,000,000 and (ii) an amount equal to 10% of Consolidated TTM EBITDA at any time outstanding.

## Pattern 2: lender, false_answer (7 cases)

gold is unresolved, model gave a value.

- `fx0012` gold: `unresolved` | predicted: `LC Commitment`
  > 20 “ LC Commitment ” means, with respect to CoBank, as Issuing Bank, $50,000,000; provided that the LC Commitment shall be reduced by the amount of any Letters of Credit issued and outstanding under the second sentence of the definition of Letters of Credit. For the avoidance of doubt, any Lender that is an Issuing Bank pursuant to the second sentence of the definition of Issuing Bank shall not have any LC Commitment ...

- `fx0015` gold: `unresolved` | predicted: `Rayonier`
  > 6 the Administrative Agent and Rayonier). With respect only to the calculation of interest on 2022 Incremental Term Loan Advances, the all-in interest rate with respect to such 2022 Incremental Term Loan Advances shall be increased or decreased, as applicable, by the amount of such difference (in a like amount of basis points), which increase or decrease shall commence from and as of such Reset Date and shall remain  ...

## Pattern 3: interest_margin, missed (5 cases)

gold has an answer, model said unresolved.

- `fx0043` gold: `0.75%` | predicted: `unresolved`
  > The principal amount of the Loan outstanding from time to time shall bear interest at the variable Wall Street Journal Prime Rate plus 0.75% per annum. "Wall Street Journal Prime Rate" shall mean that variable interest rate which is subject to change from time to time based upon changes in the independent index which is the Prime Rate as published in the Wall Street Journal (the "Index"). The Index is not necessarily ...

- `fx0261` gold: `2.75%` | predicted: `unresolved`
  > 1. Rate . Prior to the Maturity Date or an Event of Default, the Rate shall be the LESSER of (a) the MAXIMUM RATE , or (b) PRIME RATE PLUS TWO AND 75/100 PERCENT (2.75%), per annum, ADJUSTED QUARTERLY ON THE FIRST DAY OF EACH CALENDAR QUARTER . However, notwithstanding the foregoing; (i) the Rate will never be less than TEN AND 50/100 PERCENT (10.50%) per annum; and (ii) from and after the Maturity Date, the Rate sha ...
