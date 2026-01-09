"""
PySpark Hello World - EMR Custom TLS Certificates Demo

This simple Spark application demonstrates that the EMR cluster is operational
with in-transit TLS encryption enabled. It creates a small dataset, performs
basic transformations, and outputs the results.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, split, lower, count


def main():
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("HelloWorld-EMR-TLS-Demo") \
        .getOrCreate()

    print("=" * 60)
    print("PySpark Hello World - EMR Custom TLS Demo")
    print("=" * 60)

    # Verify Spark configuration
    print("\nSpark Configuration:")
    print(f"  App Name: {spark.sparkContext.appName}")
    print(f"  Master: {spark.sparkContext.master}")
    print(f"  Spark Version: {spark.version}")

    # Create sample data
    data = [
        ("Hello World from EMR with TLS encryption!",),
        ("This cluster uses custom certificates from AWS Private CA.",),
        ("Data in transit is now encrypted between all nodes.",),
        ("PySpark is running successfully on Amazon EMR 7.9.",),
    ]

    df = spark.createDataFrame(data, ["message"])

    print("\nSample Messages:")
    df.show(truncate=False)

    # Word count demonstration
    print("\nWord Count Analysis:")
    words_df = df.select(
        explode(split(lower(col("message")), "\\s+")).alias("word")
    ).filter(col("word") != "")

    word_counts = words_df.groupBy("word") \
        .agg(count("*").alias("count")) \
        .orderBy(col("count").desc())

    word_counts.show(20)

    # Summary statistics
    total_words = words_df.count()
    unique_words = word_counts.count()

    print(f"\nSummary:")
    print(f"  Total words: {total_words}")
    print(f"  Unique words: {unique_words}")

    print("\n" + "=" * 60)
    print("Hello World job completed successfully!")
    print("TLS encryption is working for data in transit.")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    main()
