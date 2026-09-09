# Retail Customer Analytics & Segmentation Platform

An end-to-end customer analytics platform built on transactional e-commerce data.

The project demonstrates a practical analytics workflow from raw source data through analytical modeling, validation, customer segmentation, performance benchmarking, and an interactive decision-support dashboard.

## Project Overview

The platform transforms source-grain e-commerce data into business-ready analytical datasets that support:

- Customer-level analysis
- RFM segmentation
- Cohort retention analysis
- Revenue and order performance analysis
- Product-category analysis
- Geographic analysis
- Customer-level drill-downs
- Automated business insights
- SQL performance benchmarking

The system is designed around a layered analytical architecture:

    Raw CSV data
          |
          v
       Bronze
          |
          v
        Silver
          |
          v
         Gold
          |
          +------------------+
          |                  |
          v                  v
    Data Quality        Performance
          |                  |
          +--------+---------+
                   |
                   v
            Analytics Layer
                   |
                   v
          Streamlit Dashboard

## Tech Stack

- Python
- SQL
- DuckDB
- Pandas
- Plotly
- Streamlit
- Pytest

## Architecture

### Bronze Layer

The Bronze layer ingests the source CSV files with minimal transformation.

Its purpose is to preserve source-grain data and provide a reproducible foundation for downstream transformations.

### Silver Layer

The Silver layer converts the source data into typed and normalized analytical tables.

Core entities include:

- Customers
- Orders
- Order items
- Products
- Sellers
- Payments
- Reviews
- Category translation

Timestamp and numeric fields are converted into analytical data types at this stage.

### Gold Layer

The Gold layer contains business-ready analytical marts rather than raw transactional structures.

Current analytical marts include:

- `gold.customer_order_history`
- `gold.customer_360`
- `gold.monthly_kpis`
- `gold.state_monthly_kpis`
- `gold.category_kpis`
- `gold.state_category_kpis`
- `gold.cohort_retention`
- `gold.customer_rfm`
- `gold.customer_segments`
- `gold.segment_summary`
- `gold.state_segment_summary`
- `gold.business_insights`

This separation allows the dashboard and analytical queries to operate on purpose-built datasets rather than repeatedly reconstructing business logic from raw tables.

## Repository Structure

    Retail_Customer_Analytics/
    |
    â”œâ”€â”€ artifacts/
    â”‚   â””â”€â”€ benchmark_results.json
    |
    â”œâ”€â”€ data/
    â”‚   â”œâ”€â”€ raw/
    â”‚   â””â”€â”€ warehouse/
    |
    â”œâ”€â”€ docs/
    â”‚   â”œâ”€â”€ data_dictionary.md
    â”‚   â””â”€â”€ methodology.md
    |
    â”œâ”€â”€ scripts/
    â”‚   â”œâ”€â”€ benchmark.py
    â”‚   â”œâ”€â”€ build_warehouse.py
    â”‚   â”œâ”€â”€ diagnose_benchmark.py
    â”‚   â”œâ”€â”€ fetch_data.py
    â”‚   â””â”€â”€ setup_project.py
    |
    â”œâ”€â”€ sql/
    â”‚   â”œâ”€â”€ 01_silver.sql
    â”‚   â”œâ”€â”€ 02_gold.sql
    â”‚   â”œâ”€â”€ 03_quality.sql
    â”‚   â””â”€â”€ 04_performance.sql
    |
    â”œâ”€â”€ src/
    â”‚   â”œâ”€â”€ analytics.py
    â”‚   â”œâ”€â”€ app.py
    â”‚   â”œâ”€â”€ config.py
    â”‚   â””â”€â”€ db.py
    |
    â”œâ”€â”€ tests/
    â”‚   â””â”€â”€ test_warehouse.py
    |
    â”œâ”€â”€ .gitignore
    â””â”€â”€ requirements.txt

## Dataset

The project uses the Brazilian E-Commerce Public Dataset from Olist.

The dataset contains approximately 100,000 e-commerce orders together with related customer, order, product, seller, payment, and review information.

Dataset source:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

The raw dataset files are intentionally excluded from version control.

## Core Analytical Workloads

### Customer 360

`gold.customer_360` provides a customer-level analytical view containing:

- First order date
- Last order date
- Order count
- Total revenue
- Average order value
- Total items
- Average review score
- Customer state
- Customer city

This mart supports both aggregate analysis and individual customer drill-downs.

### RFM Segmentation

Customer behavior is summarized using three dimensions:

**Recency**

How recently the customer placed their last purchase.

**Frequency**

How many orders are associated with the customer.

**Monetary Value**

The customer's total revenue under the project's revenue definition.

Customers are scored into five quantile buckets using `NTILE(5)` and assigned to behavioral segments.

Current segments include:

- Champions
- Loyal Customers
- Potential Loyalists
- At Risk
- Hibernating
- Needs Attention

### Cohort Retention

Customers are grouped by the calendar month of their first qualifying purchase.

Subsequent purchasing behavior is tracked by the number of months elapsed since that first purchase.

The retention mart contains:

- Cohort month
- Order month
- Month number
- Active customers
- Cohort size
- Retention rate

### Commercial Analysis

The analytical layer supports analysis of:

- Revenue
- Orders
- Unique customers
- Average order value
- Product revenue
- Freight value
- Gross merchandise value
- Items sold
- Category performance
- Geographic performance
- Segment contribution

### Geographic Analysis

State-level analytical marts allow the same business questions to be evaluated across customer geographies.

The dashboard currently supports customer-state filtering across:

- Executive KPIs
- Monthly performance trends
- Customer Segments
- Commercial Performance
- Customer Explorer

The Cohort Retention view currently represents the overall customer base.

The automated Key Findings also currently summarize the overall customer base rather than changing with the selected state.

## Revenue Definition

Revenue-oriented customer metrics exclude orders whose status is:

- `canceled`
- `unavailable`

Order value is calculated as:

    product price + freight value

Customer-level analysis uses `customer_unique_id` so repeat orders associated with the same underlying customer can be analyzed together.

## Business Insights

The Gold layer also contains `gold.business_insights`.

This table converts analytical results into structured findings containing:

- Insight type
- Priority
- Headline
- Detail
- Metric value
- Metric label
- Recommended action

The purpose is to keep the analytical reasoning separate from the dashboard presentation layer.

Examples of supported insight themes include:

- Highest-value customer segment
- At-risk revenue exposure
- Strongest product category
- Highest-revenue customer state
- Repeat-customer share
- Revenue concentration

## Data Quality

The project includes a dedicated quality layer with checks for:

- Required fields
- Duplicate keys
- Referential integrity
- Timestamp chronology
- Negative monetary values
- Expected warehouse tables

The quality layer is designed to surface source-data issues rather than silently hiding them.

This makes the analytical pipeline easier to audit and debug.

## Automated Tests

The repository includes Pytest coverage for core warehouse expectations.

The current test suite validates:

- Required analytical tables exist
- Customer-level marts contain data
- Customer order history contains valid records
- Orders have valid customer relationships
- Order identifiers are not duplicated
- Category analysis contains valid revenue
- Quality summaries exist

Run the test suite with:

    pytest -q

## Performance Benchmark

The project includes a reproducible benchmark comparing two implementations of the same customer-level analytical workload.

### Workload A

Join and aggregate the underlying Silver tables:

    silver.customers
        +
    silver.orders
        +
    silver.order_items

### Workload B

Read the equivalent metrics from the materialized:

    gold.customer_360

Five timed executions were performed for each workload after a warm-up execution.

The measured local results were:

| Workload | Median execution time |
|---|---:|
| Raw multi-table aggregation | 326.10 ms |
| Materialized customer mart | 207.63 ms |
| Median speedup | 1.57x |

The benchmark also validates metric equivalence before accepting the comparison:

| Validation | Result |
|---|---:|
| Raw customer count | 96,096 |
| Gold customer count | 96,096 |
| Metric equivalence | True |

The 1.57x result is specific to this workload, dataset size, local hardware, and DuckDB configuration. It should not be interpreted as a universal database performance improvement.

## Benchmark Methodology

The benchmark intentionally compares equivalent business metrics.

The raw workload performs the underlying joins and aggregations required to construct customer-level metrics.

The optimized workload reads those already-materialized metrics from `gold.customer_360`.

The benchmark therefore evaluates the practical benefit of precomputing a repeated analytical workload rather than attributing the observed difference to a single database feature.

Performance results are interpreted only after the metric-equivalence check passes.

## Reproducibility

The warehouse is generated locally rather than maintained as a manually edited database artifact.

The setup workflow is:

    source CSVs
          â†“
    fetch_data.py
          â†“
    build_warehouse.py
          â†“
    Silver + Gold + Quality + Performance layers

The complete setup can be triggered through:

    python scripts/setup_project.py

This provides a repeatable path from source data to the analytical warehouse.

Raw source data and generated database files are excluded from version control through `.gitignore`.

## Streamlit Dashboard

The dashboard is implemented in `src/app.py`.

It currently provides five primary analytical areas:

### Executive

Provides:

- Total orders
- Unique customers
- Revenue
- Average order value
- Average review score
- Monthly revenue trends
- Monthly order trends
- Monthly customer trends
- Key analytical findings

### Customer Segments

Provides:

- Customer counts by segment
- Average customer value
- Segment-level business metrics
- Revenue contribution
- Recency and frequency indicators
- Recommended actions by segment

### Commercial

Provides:

- Product-category performance
- Gross merchandise value
- Order volume
- Product revenue
- Freight value
- Average item price

### Retention

Provides cohort-based retention analysis across purchase months.

### Customer Explorer

Provides customer-level exploration and drill-downs.

An analyst can inspect:

- Customer location
- RFM segment
- RFM score
- Recency
- Frequency
- Monetary value
- Average review
- Customer order history

## Dashboard Filtering

The customer-state filter is implemented through state-aware analytical marts for the views that currently support it.

This avoids filtering unrelated pre-aggregated results directly in the presentation layer.

The retention analysis and automated Key Findings remain overall views in the current release.

## Setup

Create the virtual environment:

    python -m venv .venv

Activate it in PowerShell:

    .\.venv\Scripts\Activate.ps1

Install dependencies:

    python -m pip install -r requirements.txt

Build the warehouse:

    python scripts/setup_project.py

Run the automated tests:

    pytest -q

Run the performance benchmark:

    python scripts/benchmark.py

Launch the dashboard:

    streamlit run src/app.py

## Complete Workflow

A typical workflow is:

1. Prepare the Python environment.
2. Install dependencies.
3. Download the source data.
4. Build the analytical warehouse.
5. Run automated tests.
6. Run the benchmark.
7. Launch the Streamlit dashboard.

## Design Principles

The project deliberately separates:

- Data ingestion
- Transformation
- Analytical modeling
- Data-quality validation
- Business logic
- Performance measurement
- Presentation

The objective is to avoid putting substantial business logic directly into dashboard code.

Analytical outputs are materialized where they represent repeated business workloads, while the dashboard consumes purpose-built analytical queries.

## Limitations

This is an analytical portfolio project rather than a production transactional system.

The performance benchmark is local and workload-specific.

Results may differ with:

- Dataset size
- Hardware
- DuckDB version
- Query optimizer behavior
- Storage configuration
- Production warehouse architecture

The RFM segment definitions are analytical heuristics based on customer behavior in the available dataset.

The business recommendations represent interpretations of historical behavior. They are not causal estimates of campaign effectiveness.

The source dataset itself may contain data-quality anomalies. The project surfaces these through validation rather than assuming perfect source data.

## Dataset and Licensing Notice

The underlying Olist dataset is subject to its own license and usage terms.

This repository contains the transformation, analytical, validation, benchmarking, and dashboard code. Raw source data is not redistributed as part of the repository.

## Project Goal

The goal of the project is to demonstrate an end-to-end analytics workflow that connects:

    Data engineering
          +
    SQL analytics
          +
    Data quality
          +
    Customer analytics
          +
    Performance analysis
          +
    Business interpretation
          +
    Interactive decision support

The emphasis is on reproducibility, measurable analytical work, and clear separation between data preparation, analysis, and presentation.
