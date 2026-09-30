# CFPB Complaint Company--Product Analysis

## Purpose

This analysis organizes CFPB complaint data into a company-level product
analysis dataset. The final output is designed to support comparison of
complaint volumes across companies, products, subproducts, and issues
while also assigning each complaint category to standardized
product-line classifications.

The analysis combines complaint data covering **October 1, 2025 through
August 31, 2026** and produces a summarized output containing one row
for each unique:

**Company × Product × Subproduct × Issue**

combination.

## Source Data

The analysis uses CFPB complaint data from four source files covering:

-   October 1, 2025 -- December 31, 2025
-   January 1, 2026 -- March 31, 2026
-   April 1, 2026 -- July 31, 2026
-   August 1, 2026 -- August 31, 2026

The combined staging dataset contains **8,246,999 complaint records**,
representing **8,246,999 unique case numbers**.

The source files were loaded into DuckDB and combined into a single
staging table, `stg_complaints`.

## Data Model

The complaint data were organized into a star-schema structure
consisting of a central complaint fact table and supporting dimensions
for:

-   Date
-   Company
-   Product
-   Issue
-   Location
-   Referral information

The resulting `fact_complaint` table contains one record per complaint.

Dimension keys were validated to ensure that each key uniquely
identifies a single dimension record and that joining the fact table
individually to each dimension preserves the original complaint count.

## Company--Product Analysis

The primary analytical table, `company_product_analysis`, aggregates the
complaint-level data to:

**Company × Product × Subproduct × Issue**

For each combination, the table contains the number of complaints
associated with that company and complaint category.

For example, a row represents complaints associated with:

> Company A × Credit Card × General-Purpose Credit Card or Charge Card ×
> Specific Issue

rather than an individual consumer complaint.

As a result, the final analytical dataset is substantially smaller than
the underlying complaint-level dataset while retaining the dimensions
needed for product and issue analysis.

## Product Complaint Percentage

For each company/product combination, the analysis calculates the
company's share of complaints within the corresponding product across
**all companies**.

Conceptually:

**Company Product Complaint % = Company complaints for the product ÷
Total complaints for that product across all companies × 100**

This measure provides context for a company's complaint volume relative
to the overall complaint volume associated with that product.

It should not be interpreted as a complaint rate because the dataset
does not contain a denominator such as number of customers, accounts,
transactions, or products outstanding.

## Product / Subproduct / Issue Identifier

Each analytical row includes an identifier derived from the combination
of:

**Product + Subproduct + Issue**

The identifier allows records representing the same complaint category
to be easily filtered, grouped, or compared across companies.

Because the identifier is based on the complete Product/Subproduct/Issue
combination, companies reporting complaints in the same category share
the same identifier.

## Product-Line Classification

A separate `product_lookup` file is used to assign each Product ×
Subproduct × Issue combination to three additional analytical fields:

-   **Primary Product Line**
-   **Secondary Product Line**
-   **Furnishing**

The lookup is joined to the analytical data using the complete
combination of:

**Product × Subproduct × Issue**

Text is trimmed and normalized for case during matching to avoid
differences caused solely by capitalization or leading/trailing spaces.

The lookup table serves as the maintained classification layer. New or
revised CFPB Product/Subproduct/Issue combinations can therefore be
incorporated by updating the lookup file rather than changing the core
analysis code.

## Lookup Validation

The lookup process was validated by identifying records for which no
classification was returned.

**Product/Subproduct not found** indicates that the Product × Subproduct
combination itself was not represented in the lookup.

**Issue mismatch** indicates that the Product × Subproduct combination
existed in the lookup but the exact issue value did not.

Issue mismatches identified during development were reviewed and the
lookup table was updated with the corresponding current complaint issue
terminology before production of the final output.

This approach preserves exact and reproducible mappings rather than
relying on fuzzy text matching.

## Final Output

The final output file is:

**`company_product_analysis_augmented.csv`**

The file contains one row per:

**Company × Product × Subproduct × Issue**

and includes the complaint-volume measures, product-level comparison
measures, Product/Subproduct/Issue identifier, and product-line
classifications from the lookup table.

The final file is intended to support:

-   Company complaint profiling
-   Product-level complaint comparisons
-   Subproduct analysis
-   Issue analysis
-   Product-line reporting
-   Furnishing-related analysis
-   Filtering companies within a common Product/Subproduct/Issue
    category
-   Ranking companies by complaint volume or share within a product

## Important Interpretation Notes

Complaint counts represent complaints contained in the source data and
should not be interpreted independently as measures of company size,
market share, or consumer harm.

A company with more customers or accounts may naturally generate more
complaints than a smaller company. The product complaint percentage
measures the company's share of **complaints**, not its share of
customers or the underlying market.

Likewise, differences in complaint volume may reflect differences in
company size, product mix, consumer behavior, complaint submission
patterns, company-name matching, or other factors not measured in this
dataset.

The analysis is therefore best used to describe and compare the
**distribution of complaints in the analyzed CFPB complaint data**,
rather than as a standalone measure of company performance.

## Reproducibility

The analytical workflow follows this general sequence:

``` text
Source CSV files
      ↓
stg_complaints
      ↓
Dimension tables + fact_complaint
      ↓
company_product_analysis
      ↓
product_lookup
      ↓
company_product_analysis_augmented
      ↓
company_product_analysis_augmented.csv
```

The DuckDB database retains the intermediate staging, dimension, fact,
and analytical tables so that the final output can be reproduced and
validated from the source complaint data.

## Final Validation

Before distributing or using the final output, rerun the
unmatched-record validation after the lookup table has been finalized.
Document any remaining unmatched Product/Subproduct/Issue combinations
and their associated complaint counts. If all combinations are
successfully classified, record that the final lookup achieved complete
coverage of the analyzed complaint records.
