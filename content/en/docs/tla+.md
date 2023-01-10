---
categories: [Software]
tags: []
title: TLA+
linkTitle: TLA+
weight: 12
description: >
    TLA+ is a language for modeling software above the code level and hardware above the circuit level. The tool most commonly used by engineers is the TLC model checker, but there is also a proof checker.  TLA+ is based on mathematics and does not resemble any programming language. Most engineers will find PlusCal, described below, to be the easiest way to start using TLA+.
date created: Thursday, January 5th 2023, 12:18:20 am
date modified: Tuesday, January 10th 2023, 9:42:01 am
---

{{% pageinfo %}}

WIP: Placeholder page

* [The TLA+ Home Page](https://lamport.azurewebsites.net/tla/tla.html)
* [Learn TLA+](https://www.learntla.com/index.html)
* [Use of Formal Methods at AWS](http://lamport.azurewebsites.net/tla/formal-methods-amazon.pdf)

{{% /pageinfo %}}

## TLA+

### PlusCal

```
---- MODULE pluscal ----
EXTENDS Integers, TLC

(* --algorithm pluscal
variables
 x = 2;
 y = TRUE;

begin
  A:
    x := x + 1;
  B:
    x := x + 1;
    y := FALSE;
end algorithm; *)
====
```

### Labels

### Invariants

### Specifications
