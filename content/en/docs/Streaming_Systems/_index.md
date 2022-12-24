---
categories: ["Data", "Software"]
title: "Streaming Systems"
linkTitle: "Streaming Systems"
weight: 4
date: 2022-05-26
description: >
  Streaming systems are computer systems designed to continuously process and analyze data as it is generated or received in real time, allowing organizations to extract insights and take action on data as it becomes available, rather than having to wait for data to be stored and processed in batch.
---

{{% pageinfo %}}
This is a placeholder page for streaming systems
{{% /pageinfo %}}

{{% blocks/section type="section" color="white" %}}
## Resources

* [The Log: What every software engineer should know about real-time data's unifying abstraction](https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying)
* [The world beyond batch - streaming 101](https://www.oreilly.com/radar/the-world-beyond-batch-streaming-101/)
* [The world beyond batch - streaming 102](https://www.oreilly.com/radar/the-world-beyond-batch-streaming-102/)
* [Netflix - Keystone](https://netflixtechblog.com/keystone-real-time-stream-processing-platform-a3ee651812a)
* [Netflix - Mantis](https://netflixtechblog.com/stream-processing-with-mantis-78af913f51a6)
* [Netflix - Kafka + Keystone](https://medium.com/netflix-techblog/kafka-inside-keystone-pipeline-dd5aeabaf6bb)
* [Databricks - CDC DLT](https://databricks.com/blog/2022/04/27/how-uplift-built-cdc-and-multiplexing-data-pipelines-with-databricks-delta-live-tables.html)
* [How does Kafka Perform when you need Low Latency](https://dzone.com/articles/how-does-kafka-perform-when-you-need-low-latency)
* [Streaming Data Exchange - Data Mesh](https://www.kai-waehner.de/blog/2021/11/14/streaming-data-exchange-data-mesh-apache-kafka-in-motion/`)
* [Kafka API De Facto Standard - Event Streaming](https://www.kai-waehner.de/blog/2021/05/09/kafka-api-de-facto-standard-event-streaming-like-amazon-s3-object-storage/)
* [Apache Kafka and the Data Mesh](https://www.confluent.io/events/kafka-summit-europe-2021/apache-kafka-and-the-data-mesh/)
* [Flink w/ RocksDB on AKS](https://towardsdatascience.com/running-apache-flink-with-rocksdb-on-azure-kubernetes-service-904181d79f72)
* [Event Types in Kafka Topics](https://martin.kleppmann.com/2018/01/18/event-types-in-kafka-topic.html)
* [History of Apache Storm and Lessons Learned](http://nathanmarz.com/blog/history-of-apache-storm-and-lessons-learned.html)
* [Processing Billions of Events in Real Time at Twitter](https://blog.twitter.com/engineering/en_us/topics/infrastructure/2021/processing-billions-of-events-in-real-time-at-twitter-)
* [Benefits of using Kafka to Handle RTDS](https://acceldataio.medium.com/benefits-of-using-kafka-to-handle-real-time-data-streams-662e9dfc09fe)
* [RTDP Arch - Spark + Kafka + ClickHouse](https://medium.com/whatfix-techblog/real-time-data-processing-architecture-using-apache-spark-apache-kafka-and-click-house-ab8e98ad3f98)
* [Streaming Windows Event Logs](https://databricks.com/blog/2022/05/05/streaming-windows-event-logs-into-the-cybersecurity-lakehouse.html)
* [Cube Materialize Integration](https://cube.dev/blog/materialize-integration)
* [Litestream](https://github.com/benbjohnson/litestream)
* [Slack - Building Self Driving Kafka Clusters](https://slack.engineering/building-self-driving-kafka-clusters-using-open-source-components/)
* [Apache Kafka - Refcard](https://dzone.com/refcardz/apache-kafka)
* [Apache ActiveMQ vs Kafka](https://www.baeldung.com/apache-activemq-vs-kafka)
* [Streaming Applications on Serverless Spark](https://selectfrom.dev/streaming-applications-on-serverless-spark-66f282a29b7c)
* [Live Analytics - Materialize](https://materialize.com/docs/quickstarts/live-analytics/)
* [Rill Data - Apache Druid - DuckDB](https://www.rilldata.com/)
* [Managed Kafka Services - Which one is right for you?](https://developers.redhat.com/articles/2022/05/24/managed-kafka-services-which-right-you#what_kafka_distribution_is_right_for_you_)
* [Streaming Data](https://medium.com/@samueldavidwinter/streaming-data-9d8a3967f7ee)
* [Building a search index with Kafka and Elasticsearch](https://quastor.substack.com/p/building-a-search-index-with-kafka?s=r)
* [Streaming Graph Library](https://quine.io/)
* [RisingWave similar to Materialize](https://www.risingwave.dev/docs/latest/intro/)
* [Graph Databases](https://www.thatdot.com/blog/understanding-the-scale-limitations-of-graph-databases)
* [Microsoft - Intro to Data Streaming](https://docs.microsoft.com/en-us/learn/modules/introduction-to-data-streaming/)
* [Databricks - What is Spark Streaming](https://databricks.com/glossary/what-is-spark-streaming)
* [How Uplift built CDC and Multiplexing data pipelines with Databricks Delta Live Tables](https://www.databricks.com/blog/2022/04/27/how-uplift-built-cdc-and-multiplexing-data-pipelines-with-databricks-delta-live-tables.html)

## Existing Tools

* [Apache Beam](https://beam.apache.org/)
  * [GCP Dataflow](https://cloud.google.com/dataflow)
* [Apache Flink](https://flink.apache.org/)
  * [AWS Kinesis](https://aws.amazon.com/kinesis/)
* [Apache Spark](https://spark.apache.org/docs/latest/streaming-programming-guide.html)
  * [Databricks](https://www.databricks.com)
* [Apache Kafka](https://kafka.apache.org/)
  * [Redpanda](https://redpanda.com/)
  * [Confluent](https://www.confluent.io/)
* [Akka Platform](https://www.lightbend.com/akka-platform)
  * [Akka Streams](https://doc.akka.io/docs/akka/current/stream/index.html)
  * [Cloudflow](https://cloudflow.io/)
* [Hazelcast - Jet](https://jet-start.sh/)
* [Fluvio](https://www.fluvio.io/)
* [Apache Pulsar](https://pulsar.apache.org/)
* [NATS Jetstream](https://docs.nats.io/nats-concepts/jetstream/streams)
* [RabbitMQ Streams](https://www.rabbitmq.com/stream.html)
* [Azure EventHub](https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-about)
* [Apache Heron](https://heron.apache.org/)
* [Apache Storm](https://storm.apache.org/)
* [Apache Samza](https://samza.apache.org/)
* [MemQ](https://github.com/pinterest/memq)
* [Twister2](https://twister2.org/)
* [Faust](https://github.com/faust-streaming/faust)

{{% /blocks/section %}}
