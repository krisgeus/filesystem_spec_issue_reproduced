import logging
import time
import fsspec
from pyarrow.dataset import dataset

# logging.basicConfig(level=logging.DEBUG)

time.sleep(30)

url = 'http://mockserver:1080/demo-s3-output/output/data/demo/spark/cars-all/part-00000-7512f0aa-e860-483c-aea5-e6bb2dd493ac-c000.snappy.parquet?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20210712T192424Z&X-Amz-SignedHeaders=host&X-Amz-Expires=900&X-Amz-Credential=test%2F20210712%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=a5daeb3fec5cf0ac7f1dce877c41b0c8c24eab7b63c72a3f1d8d8f9e2e4ef6e9'

filesystem = fsspec.filesystem('http')
pdf = (
    dataset(source=url, format="parquet", filesystem=filesystem)
    .to_table()
    .to_pandas()
)

print(pdf.head())
