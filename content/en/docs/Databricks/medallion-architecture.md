---
weight: 
categories: ["Data"]
tags: ["databricks", "data-science", "bi", "best-practices", "architecture", "data-lake"]
title: "Medallion Architecture"
linkTitle: "Medallion Architecture"
description: >
  Medallion architecture is a data storage solution that uses a tiered approach to manage data within a Lakehouse, with the bronze layer representing raw data, the silver layer representing transformed or aggregated data, and the gold layer representing data that is ready for consumption or analysis.
date created: Friday, December 23rd 2022, 7:06:08 pm
date modified: Wednesday, January 4th 2023, 11:19:29 pm
---

{{% pageinfo %}}

These are just quick n dirty notes, will fill this out with more substance another time.

{{% /pageinfo %}}

## Medallion Architecture

### Bronze

* Append only
* Retain everything
* Soft-deletes if necessary
* Hard-deletes if required by regulatory reasons
* Don't parse the underlying data,

### Silver

* Ease of query
* Clean data
* ACID transactions
* Enterprise data model
  * 3rd normal form
  * De-normalisation for performance reasons
* Uses Delta Lake tables
* Preserves grain of original data (no aggregation)
* Eliminates duplicate records
* Enforce production schema

### Gold Layer

* Designed for a particular user community
* Reduces costs associated with ad hoc queries
* Allows fine grained permissions
* Power ML applications, reporting, dashboards, ad hoc analytics
* Shifts query updates to production workloads
