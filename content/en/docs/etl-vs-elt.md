---
categories: [Data]
tags: [etl, elt]
title: ETL vs ELT
linkTitle: ETL vs ELT
weight: 11
description: >
    Extract, Transform and Load (where the transform phase and load phase can be swapped) refers to processes for organising a data pipeline into conceptual or actual phases or stages.
date created: Thursday, January 5th 2023, 11:20:56 am
date modified: Tuesday, January 10th 2023, 11:39:14 am
---

{{% pageinfo %}}

WIP: Incomplete.

We worked on this for the Thinkathon in 2023 Aginic Bootcamp and while it was an entertaining exercise I felt unsatisfied with the brief overview we were able to cover. I personally would like a more thorough analysis of the differences, reasons and best practices regarding the topic.

What do you think? Leave a comment below if you feel this would be worthwhile.

{{% /pageinfo %}}

Extract Transform Load vs Extract Load Transform

## Extract Transform Load (ETL)

* Has been used by data engineers since the 1970s. [₁][1]
* Primarily used for relational data warehouses where the sources may be varied but the destination only supports structured data.

### Pros

* Cheaper storage
* The extract and transform stages are typically combined, allowing for faster access to insights because the data is immediately available once it is loaded

### Cons / Challenges

* Potential loss of data, when transformation fails on highly volatile data
* If the source data is changing, it can be impossible to re-run the process on the original data when a problem is discovered changes
* Multiple downstream sources might need same source data, increasing pressure on source system

## Extract Load Transform (ELT)

> It's probably more like ELTLTLTL

### Pros

* Can be more robust as replicating data is less complex than transforming and so if the pipeline has problems in the transformation stage, it can be rerun from the raw data without disturbing
* Can re-run pipelines on the same data if anything goes wrong
* Process is more staged

### Cons / Challenges

* Increased storage cost, keeping raw data
* Governance (GDPR / HIPAA / CCPA) can be more difficult to do right:
    * TODO: Re-find the article that made this argument

## References

[1]: https://www.ibm.com/cloud/blog/elt-vs-etl-whats-the-difference
[2]:https://rivery.io/blog/etl-vs-elt/
[3]: https://www.guru99.com/etl-vs-elt.html
[4]: https://www.integrate.io/blog/etl-vs-elt/
[5]: https://www.snowflake.com/guides/etl-vs-elt
[6]: https://visualbi.com/blogs/featured/data-architecture-engineering/evolution-of-etl-to-elt/
