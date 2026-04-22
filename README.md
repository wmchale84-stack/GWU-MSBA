# CFPB Consumer Complaints Analysis - Group 14
**Course:** DNSC 6305 - Data Management for Analytics

## ABOUT THIS DATA

This download contains consumer complaint data from the Consumer Financial Protection Bureau (CFPB) Consumer Complaint Database. The CFPB is a U.S. government agency responsible for consumer protection in the financial sector. This database is updated daily to include complaints submitted by consumers about financial products and services that the CFPB sends to companies for response. The Consumer Complaint Database is an important resource for understanding the experiences of consumers with financial products. It highlights problematic practices by financial institutions and analyzes patterns regarding consumer financial issues. Complaints are only included in the database once the company responds and confirms a commercial relationship with the consumer. If the company fails to respond to the complaint for 15 days, it will also be included.

For detailed information about the CFPB and the complaint process, please refer to the official CFPB documentation and the API field definitions.
* [CFPB API Field Definitions](https://cfpb.github.io/api/ccdb/api.html)
* [Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/#get-the-data)
 


## **Data Source & Project Context**

**Course**: DNSC 6305 - Data Management for Analytics, Fall 2025
                                        
**Instructor**: Dr. Ali Obaidi
                                        
**Team**: Group 14 (William McHale, Acadia Grenier, Ryan Patel, Yusuf Ozdemir Arslan)

**Data Source**: https://cfpb.github.io/api/ccdb/api.html

**Project Scope**: Our project seeks to analyze a filtered subset of the complete CFPB database, focusing on a range of complaints from July 2024 to July 2025. We sought to enable meaningful business intelligence analysis while also navigating possible computational constraints. This database is updated daily, and at the point of sourcing, the original database contained over 21 million complaint records spanning from 2011 to the present.

**Academic Context**: This data analysis is part of DNSC 6305 (Data Management for Analytics) coursework, demonstrating end-to-end data analytics, including data acquisition, dimensional modeling, SQL querying, and business intelligence visualization.

## **Dimensional Model Overview**: 

To structure our data, we utilized dimensional modeling principles in tandem with a star schema design. Our approach separated transactional facts from their descriptive dimensions, better optimizing the database for analytical queries and further business intelligence.

### Star Schema Components

**Fact Table:**

**`fact_complaint`** = Main fact table, containing one record per complaint with foreign keys to all dimension tables and degenerate dimension (Complaint_ID)

**Dimension Tables:**

* `dim_date` = Temporal information - date received, date sent to company
* `dim_company` = Company identification, company details
* `dim_product` = Product and sub-product categorization
* `dim_issue` = Issue and sub-issue categorization
* `dim_location` = Geographic information - state, ZIP code
* `dim_submitted_via` = The medium used to submit the complaint to the CFPB
* `dim_consent` = Consumer consent status for publication

**Fact Table Grain:**

Each row represents one unique consumer complaint, meaning the fact table is at the individual complaint grain, allowing for maximum possible analytical flexibility and better supports aggregations at various levels: product, by company, time period, geography, etc. 

## **The Main Data Tables**

fact_complaint = Represents a single consumer complaint submitted to the CFPB. One complaint is a unique transaction where a consumer reports an issue with the service of a financial institution or its product.

Notes:

* `complaint_id` = the degenerate dimension serving as the unique identifier for each complaint
* `date_received_key` = links to dim_date for the date CFPB received the complaint
* `date_sent_key` = links to dim_date for the date CFPB sent the complaint to the company
* `company_key` = refers to the dim_company table
* `product_key` = refers to the dim_product table
* `issue_key` = refers to the dim_issue table
* `location_key` = refers to the dim_location table
* `submission_key` = refers to the dim_submitted_via table
* `consent_key` = refers to the dim_consent table
* `timely_response` = whether the company responded within the required timeframe - Yes/No
* `consumer_disputed` = whether the consumer disputed the company's response - Yes, No, N/A

**`dim_date`** = Provides temporal context for the complaints, supports time-based analysis and trending
                                     
Notes:

* `date_key` = the primary key/surrogate key
* `full_date` = the actual date value
* `year, month, day` = date part, enables grouping and filtering
* Two tracked date types: date received by CFPB, date sent to the company

**`dim_company`** = information regarding the financial institutions that are the subject of complaints

Notes:

* `company_key` = the primary key/surrogate key
* `company_name` = the name of the financial institution
* `Company names` = categorical variables; the same company may appear in the source data multiple times due to possible variations in naming

**`dim_product`** = responsible for categorizing the financial products and sub-products associated with complaints.

Notes:

* `product_key` = the primary key/surrogate key
* `product_name` = the type of financial product, possible examples:  "Credit card", "Mortgage", "Student loan"
* `subproduct_name` = any additional specificity, if applicable
    - this field may be NULL since not all products have sub-products
* Product categories are determined by the CFPB and are subject to change

**`dim_issue`** = outlines specific issues and sub-issues that consumers identified in their complaints

Notes:

* `issue_key` = the primary key/surrogate key
* `issue_name` = the primary problem reported by the consumer
* `subissue_name` = any additional detail, if available/provided
* All issues are categorical and depend on the product type
* Not all issues have corresponding sub-issues, in which case the field would be NULL

**`dim_location`** = the geographic information of the consumer's location

Notes:

* `location_key` = the primary key/surrogate key
* `state` = noted by a states corresponding two-letter abbreviation; found from the consumer's mailing address
* `zip_code` = the ZIP code found from the consumer's mailing address
* Zip codes may be truncated to 3 digits to conserve the privacy of consumers who live in a Census ZCTA with fewer than 20,000 people, must have consented to narrative publication
* Complaints may have NULL location data if it wasn't provided by the consumer

**`dim_submitted_via`** = Notes how a complaint was submitted to the CFPB.

Notes:

* `submission_key` = the primary key/surrogate key
* `submitted_via` = the submission method, possible mediums include: "Web", "Phone", "Referral", "Postal mail"
* This dimension helps to analyze consumer preferences and the accessibility of complaint channels

**dim_consent** = whether consumers consented to the publication of their complaint narrative

Notes:

* `consent_key` = the primary key/surrogate key
*`consent_status` = the consent state, possible values include:
    - "Consent provided" = the consumer opted to share their narrative
    - "Consent not provided" = the consumer did not opt in
    - "Consent withdrawn" = the consumer initially opted in but later withdrew consent
    - "N/A" = the complaint received before March 19, 2015, or the narrative publication is not available
    - "Other" = the complaint does not meet criteria for narrative publication
* All consumer narratives contain personal descriptions outlining the situation but have since removed any personal information prior to publication

## **Data Field Descriptions**

The key fields from the original CFPB dataset and how they map to our dimensional model:

### Original Source Fields:

**Date received**: When the complaint was received by the CFPB (date, time)
* Maps to: `dim_date.full_date` via `fact_complaint.date_received_key`

**Product**: How the complaint specified the type of product (categorical)
* Maps to: `dim_product.product_name`

**Sub-product**: Type of sub-product identified by the consumer (categorical, sub-products are not always given by every product)
* Maps to: `dim_product.subproduct_name`

**Issue**: The issue the consumer identified in the complaint (categorical, dependent on the product)
* Maps to: `dim_issue.issue_name`

**Sub-issue**: Sub-issue as identified by the consumer (categorical, dependent on both product and issue, issues don't always have sub-issues)
* Maps to: `dim_issue.subissue_name`

**Consumer complaint narrative**: Consumer-submitted description of the events (plain text, optional)
* Note: This field is not included in the dimensional model due to privacy considerations and focus on quantitative analysis

**Company public response**: Optional, the company's public-facing response to the complaint (plain text)
* Note: Not included in the dimensional model since we focus on complaint metrics rather than response text

**Company**: The complaint is about this company (categorical)
* Maps to: `dim_company.company_name`

**State**: State corresponding to the mailing address, provided by the consumer (categorical)
* Maps to: `dim_location.state`

**ZIP code**:  Provided ZIP code of the consumer (5-digit, 3-digit for privacy)
* Maps to: `dim_location.zip_code`

**Tags**: Data supporting easier searching and sorting, possible examples: "Older American", "Servicemember"
* Note: Not included in the current dimensional model

**Consumer consent provided?**: Whether the consumer opted to publishing their complaint narrative (categorical)
* Maps to: `dim_consent.consent_status`

**Submitted via**: How the complaint was submitted to the CFPB (categorical)
* Maps to: `dim_submitted_via.submitted_via`

**Date sent to company**: Date when CFPB sent the complaint to the company (date, time)
* Maps to: `dim_date.full_date` via `fact_complaint.date_sent_key`

**Company response to consumer**: How the company responded (categorical)
* Note: Not included in the current dimensional model

**Timely response?**: If the company gave a response within the 15 day timeframe (Yes/No)
* Maps to: `fact_complaint.timely_response`

**Consumer disputed?**: If the consumer disputed the company's response (Yes/No/N/A)
* Maps to: `fact_complaint.consumer_disputed`
* Note: This option was discontinued on April 24, 2017

**Complaint ID**: Unique identification number of a complaint (number)
* Maps to: `fact_complaint.complaint_id` = degenerate dimension

### Database Implementation

This project uses DuckDB as the database management system. DuckDB is an analytical database designed for complex analytical queries and is well-suited for business intelligence workloads using big data

### Loading Data into DuckDB

Our data pipeline consists of six stages:
* `Data Acquisition` = Download of the complete CFPB Consumer Complaint Database CSV file
* `Data Filtering` = Filter data to focus on a specific time period/subset
* `Schema Creation` = Create fact and dimension tables using DuckDB
* `Data Transformation` = Extract distinct values for dimension tables
* `Data Loading` = Populated dimension tables, then populated fact tables with foreign keys
* `Verification` = Validated record counts and data integrity

Downloading the complete CFPB Consumer Complaint Database CSV file using CSVkit

```
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import os
```

```
!wget https://files.consumerfinance.gov/ccdb/complaints.csv.zip
```

```
!unzip complaints.csv.zip
```

```
!wc -l complaints.csv
```

```
!head -n 5 complaints.csv
```

```
!head -n 5 complaints.csv | qsv table
```

```
!head -n 5 complaints.csv | csvlook
```

Connecting to the DuckDB Database:

```
duckdb.sql("""
DROP TABLE IF EXISTS complaints;

CREATE TABLE complaints AS
SELECT *
FROM read_csv('complaints.csv')
""")
```
    
```
duckdb.sql("SELECT COUNT(*) FROM complaints")
```

```
duckdb.sql("""
    SELECT *
    FROM complaints
    LIMIT 5
    """).df()
```

Excerpts on how we created the fact table with foreign keys:

```
duckdb.sql("""
DROP TABLE IF EXISTS dim_company;

CREATE TABLE dim_company (
    company_key BIGINT,
    company_name TEXT NOT NULL,
    PRIMARY KEY(company_key)
);
""")
```

```
duckdb.sql("""
DROP TABLE IF EXISTS fact_complaint;

CREATE TABLE fact_complaint (
    fact_complaint_key BIGINT,
    complaint_id BIGINT NOT NULL,

    date_received_key BIGINT REFERENCES dim_date(date_key),
    date_sent_key BIGINT REFERENCES dim_date(date_key),

    company_key BIGINT REFERENCES dim_company(company_key),
    product_key BIGINT REFERENCES dim_product(product_key),
    issue_key BIGINT REFERENCES dim_issue(issue_key),
    location_key BIGINT REFERENCES dim_location(location_key),
    submission_key BIGINT REFERENCES dim_submitted_via(submission_key),
    consent_key BIGINT REFERENCES dim_consent(consent_key),

    timely_flag INTEGER CHECK (timely_flag IN (0,1)),
    disputed_flag INTEGER CHECK (disputed_flag IN (0,1)),
    complaint_count INTEGER DEFAULT 1,

    PRIMARY KEY(fact_complaint_key)
);
""")
```

## Business Questions

* **Business Question 1**: How has the rate of untimely responses changed over time for Student Loan complaints?
* **Business Question 2**: Which companies receive the largest share of Credit Reporting complaints, and how concentrated is the market?
* **Business Question 3**: Which issues generate the most consumer complaints?
* **Business Question 4**: Which states have the highest rate of untimely responses?

### Sample Queries
The dimensional model enables efficient analytical queries. Below are the SQL queries used to answer the project's four key business questions.

**Business Question 1: How has the rate of untimely responses changed over time for Student Loan complaints?**

This query analyzes the trend of untimely company responses to student loan complaints over time by calculating the monthly untimely response counts and rates. Responsiveness is extremely relevant considering timely responses are a CFPB regulatory requirement under their 15-day mandate.

```
q1_df = duckdb.sql("""WITH base AS (
    SELECT
        d.year,
        d.month,
        f.timely_flag
    FROM fact_complaint f
    JOIN dim_date d ON f.date_received_key = d.date_key
    JOIN dim_product p ON f.product_key = p.product_key
    WHERE
        d.full_date BETWEEN DATE '2024-07-01' AND DATE '2025-06-30'
        AND p.product_name = 'Student loan'
)
SELECT
    year,
    month,
    COUNT(*) FILTER (WHERE timely_flag = 0) AS untimely_total,
    COUNT(*) AS total_complaints,
    ROUND((COUNT(*) FILTER (WHERE timely_flag = 0)*1.0 / COUNT(*)), 4) AS pct_untimely
FROM base
GROUP BY year, month
ORDER BY year, month;
""").df()
q1_df
```

**Key Insight**: The analysis demonstrates a dramatic spike in untimely responses starting in February 2025, coinciding with the CFPB enforcement shutdown, where the untimely response rate peaked at ~50% in May 2025.

**Business Question 2: Which companies receive the largest share of Credit Reporting complaints, and how concentrated is the market?**

This query investigates the market concentration within the credit reporting industry by calculating the share of total credit reporting complaints attributed to each company between July 2024 and June 2025.

```
q2_df = duckdb.sql("""
WITH filtered AS (
    SELECT f.company_key
    FROM fact_complaint f
    JOIN dim_product p ON f.product_key = p.product_key
    JOIN dim_date d ON f.date_received_key = d.date_key
    WHERE d.full_date >= DATE '2024-07-01'
      AND d.full_date <= DATE '2025-06-30'
      AND p.product_name LIKE '%Credit reporting%'
)
SELECT 
    c.company_name,
    COUNT(*) AS complaint_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM filtered), 2) AS proportion_pct
FROM filtered f
JOIN dim_company c ON f.company_key = c.company_key
GROUP BY c.company_name
ORDER BY complaint_count DESC
LIMIT 10;
""").df()
q2_df
```

**Key Insight**: The Credit reporting industry shows significant market concentration, with the "Big Three" bureaus (TransUnion, Equifax, Experian) accounting for approximately 95% of total complaints, suggesting systemic issues among the largest players.

**Business Question 3: Which issues generate the most consumer complaints?**

The query pinpoints the leading frustration points in the consumer financial market by summing up the complaints by specific issue types over the period from July 2024 to June 2025.

```
q3_df = duckdb.sql("""
SELECT 
    i.issue_name,
    COUNT(*) AS complaint_count
FROM fact_complaint f
JOIN dim_issue i ON f.issue_key = i.issue_key
JOIN dim_date d ON f.date_received_key = d.date_key
WHERE d.full_date >= DATE '2024-07-01'
  AND d.full_date <= DATE '2025-06-30'
GROUP BY i.issue_name
ORDER BY complaint_count DESC
LIMIT 10;
""").df()
q3_df
```

**Key Insight**: "Incorrect information on your report" is the single most critical consumer pain point, nearly double the volume of the next most frequent issue, highlighting data accuracy as a primary systemic failure.

**Business Question 4: Which states have the highest rate of untimely responses?**

This query examines differences across the U.S. in how consumer protection is delivered by determining the rate of untimely responses for each state and territory.

```
q4_df = duckdb.sql("""
SELECT 
    l.state,
    COUNT(*) AS total_complaints,
    SUM(CASE WHEN f.timely_flag = 0 THEN 1 ELSE 0 END) AS untimely_count,
    ROUND(SUM(CASE WHEN f.timely_flag = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS untimely_rate
FROM fact_complaint f
JOIN dim_location l ON f.location_key = l.location_key
JOIN dim_date d ON f.date_received_key = d.date_key
WHERE d.full_date >= DATE '2024-07-01'
  AND d.full_date <= DATE '2025-06-30'
  AND l.state IS NOT NULL
  AND l.state != ''
GROUP BY l.state
HAVING COUNT(*) >= 500
ORDER BY untimely_rate DESC
LIMIT 10;
""").df()
q4_df
```

**Key Insight**: Geographic analysis reveals a "mainland bias," with Puerto Rico and the Virgin Islands experiencing significantly higher untimely response rates (14.2% and 9.8%) compared to mainland states.

## Some Data Quality Considerations

* **Missing Values**: Certain fields like ZIP code, sub-product, sub-issue may be NULL
* **Data Freshness**: Since complaint data is updated regularly by the CFPB, the date of a snapshot matters for trending
* **Privacy Protection**: ZIP codes and narratives can be modified to protect consumer privacy
* **Discontinued Fields**: Consumer dispute option ended April 24, 2017
* **Company Name Variations**: A company may appear with varying names
* **Complaint Resolution**: Not all complaints are resolved, meaning some may be in progress
* **Sampling Bias**: Our analysis uses a filtered subset of the complete database
