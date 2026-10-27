### rules, val split (80 passages from 27 documents)

| Field | Answerable | Exact match | F1 | Answer precision | Answer recall | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|
| facility_size | 5 | 0.887 | 0.887 | 0.357 | 1.000 | 0.526 | 1.000 | 0.825 | 0.000 | 0.120 |
| maturity | 11 | 0.950 | 0.950 | 0.733 | 1.000 | 0.846 | 1.000 | 0.812 | 0.000 | 0.058 |
| interest_margin | 4 | 0.938 | 0.938 | 0.400 | 0.500 | 0.444 | 0.500 | 0.938 | 0.500 | 0.039 |
| lender | 17 | 0.950 | 0.960 | 0.875 | 0.824 | 0.848 | 0.824 | 0.800 | 0.118 | 0.016 |
| financial_covenants | 6 | 0.963 | 0.963 | 0.714 | 0.833 | 0.769 | 0.833 | 0.912 | 0.167 | 0.027 |
| **overall** | 43 | 0.938 | 0.940 | 0.649 | 0.860 | 0.740 | 0.860 | 0.858 | 0.116 | 0.053 |

Overall exact match 95% interval (bootstrap over documents): 0.907 to 0.965.

| Document kind | Passages | Answerable | Answer F1 | EM, answerable only | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|
| long | 65 | 33 | 0.779 | 0.909 | 0.091 | 0.048 |
| short | 15 | 10 | 0.609 | 0.700 | 0.200 | 0.077 |

### rules, test split (86 passages from 27 documents)

| Field | Answerable | Exact match | F1 | Answer precision | Answer recall | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|
| facility_size | 10 | 0.884 | 0.884 | 0.474 | 0.900 | 0.621 | 0.900 | 0.779 | 0.000 | 0.118 |
| maturity | 7 | 0.977 | 0.977 | 0.778 | 1.000 | 0.875 | 1.000 | 0.895 | 0.000 | 0.025 |
| interest_margin | 5 | 0.942 | 0.942 | 0.500 | 0.600 | 0.545 | 0.600 | 0.930 | 0.400 | 0.037 |
| lender | 12 | 0.977 | 0.987 | 0.909 | 0.833 | 0.870 | 0.833 | 0.872 | 0.083 | 0.000 |
| financial_covenants | 5 | 0.953 | 0.953 | 0.667 | 0.400 | 0.500 | 0.400 | 0.965 | 0.600 | 0.012 |
| **overall** | 39 | 0.947 | 0.949 | 0.646 | 0.795 | 0.713 | 0.795 | 0.888 | 0.154 | 0.038 |

Overall exact match 95% interval (bootstrap over documents): 0.926 to 0.966.

| Document kind | Passages | Answerable | Answer F1 | EM, answerable only | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|
| long | 66 | 28 | 0.730 | 0.821 | 0.143 | 0.036 |
| short | 20 | 11 | 0.667 | 0.727 | 0.182 | 0.045 |

### llm

Not run. pending: ANTHROPIC_API_KEY is not set and 166 of 166 responses are not cached in results/llm_cache.jsonl.

### lora, val split (80 passages from 27 documents)

| Field | Answerable | Exact match | F1 | Answer precision | Answer recall | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|
| facility_size | 5 | 0.925 | 0.925 | 0.455 | 1.000 | 0.625 | 1.000 | 0.863 | 0.000 | 0.080 |
| maturity | 11 | 0.963 | 0.963 | 0.786 | 1.000 | 0.880 | 1.000 | 0.825 | 0.000 | 0.043 |
| interest_margin | 4 | 0.938 | 0.938 | 0.250 | 0.250 | 0.250 | 0.250 | 0.950 | 0.500 | 0.026 |
| lender | 17 | 0.912 | 0.925 | 0.684 | 0.765 | 0.722 | 0.765 | 0.762 | 0.059 | 0.048 |
| financial_covenants | 6 | 0.988 | 0.988 | 0.857 | 1.000 | 0.923 | 1.000 | 0.912 | 0.000 | 0.014 |
| **overall** | 43 | 0.945 | 0.948 | 0.655 | 0.837 | 0.735 | 0.837 | 0.863 | 0.070 | 0.042 |

Overall exact match 95% interval (bootstrap over documents): 0.913 to 0.973.

| Document kind | Passages | Answerable | Answer F1 | EM, answerable only | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|
| long | 65 | 33 | 0.763 | 0.879 | 0.000 | 0.034 |
| short | 15 | 10 | 0.636 | 0.700 | 0.300 | 0.077 |

### lora, test split (86 passages from 27 documents)

| Field | Answerable | Exact match | F1 | Answer precision | Answer recall | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|---|---|---|
| facility_size | 10 | 0.860 | 0.860 | 0.429 | 0.900 | 0.581 | 0.900 | 0.756 | 0.000 | 0.145 |
| maturity | 7 | 0.977 | 0.977 | 0.778 | 1.000 | 0.875 | 1.000 | 0.895 | 0.000 | 0.025 |
| interest_margin | 5 | 0.942 | 0.942 | 0.500 | 0.400 | 0.444 | 0.400 | 0.953 | 0.600 | 0.025 |
| lender | 12 | 0.942 | 0.942 | 0.733 | 0.917 | 0.815 | 0.917 | 0.826 | 0.083 | 0.054 |
| financial_covenants | 5 | 0.988 | 0.988 | 0.833 | 1.000 | 0.909 | 1.000 | 0.930 | 0.000 | 0.012 |
| **overall** | 39 | 0.942 | 0.942 | 0.618 | 0.872 | 0.723 | 0.872 | 0.872 | 0.103 | 0.051 |

Overall exact match 95% interval (bootstrap over documents): 0.915 to 0.966.

| Document kind | Passages | Answerable | Answer F1 | EM, answerable only | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|
| long | 66 | 28 | 0.788 | 0.929 | 0.036 | 0.036 |
| short | 20 | 11 | 0.571 | 0.727 | 0.273 | 0.101 |
