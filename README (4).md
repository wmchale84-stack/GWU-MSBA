# CFPB Complaint Company--Product Analysis

## Overview

This project loads CFPB consumer complaint data into DuckDB and produces
a company-level analytical file at the following grain:

**Company × Product × Subproduct × Issue**

The purpose is to make it easy to compare companies within the same CFPB
product and complaint categories while retaining a standardized
product-line classification supplied through a separate lookup file.

The workflow is intentionally designed so that changes in CFPB Product,
Subproduct, or Issue wording can generally be handled by updating the
lookup CSV rather than rewriting the analytical SQL.

## Files

The project uses:

-   Multiple CFPB complaint CSV files
-   `product_lookup.csv` --- maintained Product/Subproduct/Issue
    classification crosswalk
-   `complaints_analysis.py` --- loading, transformation, validation,
    analysis, and export script
-   `complaints_analysis.duckdb` --- persistent DuckDB database created
    by the script
-   `company_product_analysis_augmented.csv` --- final analytical output

## Source Period

The analysis developed for this project combined complaint data
covering:

**October 1, 2025 through August 31, 2026**

The original combined staging data contained **8,246,999 complaint
records**, representing **8,246,999 unique complaint case numbers**.

If the source files are later refreshed, the row counts in the newly
generated database and output should be treated as authoritative for
that run.

## Setup

Install the required Python packages if they are not already available:

``` bash
pip install duckdb pandas
```

Open `complaints_analysis.py` and update the paths in the
**CONFIGURATION** section:

``` python
DATA_DIR = Path(r"C:\path\to\your\data")
```

Also confirm the complaint filenames listed in `COMPLAINT_FILES`.

## Workflow

The script performs the following pipeline:

``` text
Complaint CSV files
        |
        v
raw_complaints
        |
        v
stg_complaints
        |
        +-----------------------------+
        |                             |
        v                             v
Dimension tables                fact_complaint
                                      |
                                      v
                         company_product_analysis
                                      |
                         + product_lookup.csv
                                      |
                                      v
                  company_product_analysis_augmented
                                      |
                                      v
                 company_product_analysis_augmented.csv
```

### 1. Raw Loading

All complaint CSV files are loaded into `raw_complaints` with DuckDB.

`union_by_name = true` is used so files are aligned by field name rather
than physical column position.

### 2. Staging

`stg_complaints` standardizes the fields needed for the analysis,
including:

-   Complaint/case number
-   Complaint date
-   Company
-   Product
-   Subproduct
-   Issue
-   Subissue
-   State
-   ZIP code
-   Submission channel
-   Other complaint attributes used in the fact table

Blank optional fields are converted to `NULL` where appropriate.

### 3. Star Schema

The script creates dimensions for:

-   Date
-   Company
-   Product
-   Issue
-   Location

and a central `fact_complaint` table containing one row per complaint.

The fact table stores surrogate dimension keys so that the
complaint-level data can be analyzed without repeatedly joining on long
text fields.

### 4. Company/Product Analysis

`company_product_analysis` aggregates the complaint-level data to one
row per:

**Company × Product × Subproduct × Issue**

The table includes:

-   `company_name`
-   `product`
-   `subproduct`
-   `issue`
-   `product_subproduct_issue_id`
-   `complaint_count`
-   `product_total_complaints`
-   `pct_of_product_complaints`

### Product Complaint Percentage

`pct_of_product_complaints` measures the complaint count on a company's
Product/Subproduct/Issue row as a percentage of all complaints in the
corresponding **Product** across all companies.

Conceptually:

``` text
Company row complaint count
-------------------------------- × 100
All complaints for that product
```

This is a **share of complaints**, not a complaint rate. It does not
control for company size, number of customers, accounts, transactions,
balances, or market share.

### Product/Subproduct/Issue Identifier

The script creates a readable identifier in this form:

``` text
Product | Subproduct | Issue
```

For example:

``` text
Credit card | General-purpose credit card or charge card | Problem with a company's investigation into an existing problem
```

The identifier can be used to filter the final file and compare all
companies associated with the exact same complaint category.

## Product Lookup

`product_lookup.csv` supplies three additional classifications:

-   `Primary Product Line`
-   `Secondary Product Line`
-   `Furnishing`

The lookup is matched using:

**Product × Subproduct × Issue**

Matching ignores capitalization and leading/trailing spaces but
otherwise requires the wording to match.

This is deliberate. The process does **not** use fuzzy matching, which
reduces the risk of silently assigning a complaint category to the wrong
classification.

## Updating CFPB Wording

If CFPB introduces a new Product/Subproduct/Issue combination or changes
an Issue description, add the appropriate combination and classification
to `product_lookup.csv`.

Then rerun the script.

The SQL does not need to be modified simply because a new valid wording
was added to the lookup.

## Mismatch Validation

After joining the lookup, the script identifies combinations without a
`primary_product_line`.

They are classified as:

### `Issue mismatch`

The Product and Subproduct combination exists in the lookup, but the
exact Issue wording does not.

This commonly indicates that the CFPB issue terminology changed or that
the lookup needs another valid issue for that Product/Subproduct pair.

### `Product/Subproduct not found`

The Product/Subproduct pair itself does not exist in the lookup.

This generally requires adding the appropriate Product/Subproduct/Issue
combination to `product_lookup.csv`.

Before producing the final deliverable, review the mismatch output,
update the lookup as appropriate, rerun the script, and confirm that the
remaining unmatched combinations are expected.

## Important Validation Checks

The script includes several checks.

### Complaint Grain

``` text
fact_rows = unique_cases
```

This confirms that the fact table still contains one row per complaint.

### Missing Dimension Keys

The fact-table validation reports missing keys for Date, Company,
Product, Issue, and Location.

Unexpected missing keys should be investigated before using the final
analysis.

### Dimension Key Uniqueness

For every dimension:

``` text
rows = unique_keys
```

This confirms that each surrogate key identifies one dimension record.

### Lookup Join Row Count

The script compares:

``` text
company_product_analysis row count
```

with:

``` text
company_product_analysis_augmented row count
```

The counts should be identical.

If the augmented table has more rows, the lookup likely contains
duplicate Product/Subproduct/Issue combinations and is causing a
one-to-many join.

## Final Output

The final file is:

``` text
company_product_analysis_augmented.csv
```

It contains one row per:

**Company × Product × Subproduct × Issue**

plus the lookup classifications.

The file can be used for:

-   Company complaint profiling
-   Product-level comparisons
-   Subproduct analysis
-   Issue analysis
-   Primary and secondary product-line reporting
-   Furnishing analysis
-   Ranking companies by complaint volume
-   Comparing companies within an exact Product/Subproduct/Issue
    combination

## Interpretation

Complaint volume should not be treated as a direct measure of company
quality, compliance, market share, or consumer harm.

Companies differ substantially in customer counts, account volumes,
transaction volumes, product mixes, and market presence. Those
denominators are not contained in the complaint dataset.

Accordingly, this analysis describes the **distribution of complaints in
the CFPB complaint data**. Additional denominator data would be needed
to calculate true complaint rates or make exposure-adjusted comparisons.

## Reproducibility

The DuckDB database is persistent. After the script runs, the
intermediate tables remain available in `complaints_analysis.duckdb` for
inspection and validation.

Useful tables include:

``` text
raw_complaints
stg_complaints
dim_date
dim_company
dim_product
dim_issue
dim_location
fact_complaint
product_lookup
company_product_analysis
company_product_analysis_augmented
```

To inspect the final table from Python:

``` python
import duckdb

con = duckdb.connect("complaints_analysis.duckdb")

con.sql("""
SELECT *
FROM company_product_analysis_augmented
LIMIT 20;
""").df()
```

## Recommended Final Check

Before distributing the CSV:

1.  Confirm the complaint and unique-case counts are reasonable.
2.  Confirm no unexpected dimension keys are missing.
3.  Confirm the lookup join did not increase the number of analytical
    rows.
4.  Review all remaining lookup mismatches.
5.  Confirm the final lookup contains every Product/Subproduct/Issue
    combination that should be classified.
6.  Export `company_product_analysis_augmented.csv`.

This preserves a transparent path from the source complaint files
through the final company/product analytical output.
