import re
import sys

from pyspark.sql import SparkSession

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "cdp_jobs.csv"
DB_NAME = sys.argv[2] if len(sys.argv) > 2 else "default"
TABLE_NAME = sys.argv[3] if len(sys.argv) > 3 else "cdp_jobs"

spark = (
    SparkSession.builder
    .appName("load_csv_to_hive_dynamic")
    .enableHiveSupport()
    .getOrCreate()
)

# Header row of the CSV becomes the column names; number of columns/rows can vary.
df = spark.read.csv(CSV_PATH, header=True, inferSchema=True, multiLine=True, escape='"')


def clean_columns(columns):
    """Make header names Hive-safe: lowercase, snake_case, unique, non-empty."""
    seen = {}
    result = []
    for i, col in enumerate(columns):
        name = re.sub(r"[^0-9a-z]+", "_", col.strip().lower()).strip("_")
        if not name:
            name = f"col_{i}"
        if name[0].isdigit():
            name = f"c_{name}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


df = df.toDF(*clean_columns(df.columns))

spark.sql(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
df.write.mode("overwrite").format("parquet").saveAsTable(f"{DB_NAME}.{TABLE_NAME}")

print(f"Hive table {DB_NAME}.{TABLE_NAME} structure:")
spark.sql(f"DESCRIBE {DB_NAME}.{TABLE_NAME}").show(truncate=False)
spark.sql(f"SELECT * FROM {DB_NAME}.{TABLE_NAME}").show(truncate=False)
print("Rows loaded:", spark.table(f"{DB_NAME}.{TABLE_NAME}").count())

spark.stop()
