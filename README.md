# Fsspec Issue reproduction

Reproduction of fsspec issue with AWS presigned urls and pyarrow.

When trying out [databricks delta sharing](https://databricks.com/blog/2021/05/26/introducing-delta-sharing-an-open-protocol-for-secure-data-sharing.html) I encountered a bug when reading the delta file into a pyarrow pandas dataset.

Investigation lead to discovering a problem in the determination of the file size within the [fsspec](https://pypi.org/project/fsspec/) python library.

this repo is setup to show the problem and prove the patch is working.

## Setup

### In short

to prove the problem I setup the smallest environment I could think of.

I used [mockserver](https://www.mock-server.com/) to mimic the request/response cycle to/from AWS/S3.

Next to that docker container I have setup 2 python containers. One with and one without the patch.

### The setup long description

#### The python code

```python
import fsspec
from pyarrow.dataset import dataset

url = 'http://mockserver:1080/demo-s3-output/output/data/demo/spark/cars-all/part-00000-7512f0aa-e860-483c-aea5-e6bb2dd493ac-c000.snappy.parquet?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20210712T192424Z&X-Amz-SignedHeaders=host&X-Amz-Expires=900&X-Amz-Credential=test%2F20210712%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=a5daeb3fec5cf0ac7f1dce877c41b0c8c24eab7b63c72a3f1d8d8f9e2e4ef6e9'

filesystem = fsspec.filesystem('http')
pdf = (
    dataset(source=url, format="parquet", filesystem=filesystem)
    .to_table()
    .to_pandas()
)

print(pdf.head())
```

The above url is an example of a AWS S3 pre-signed url to a parqeut file on S3. Before reading in the file as a pyarrow dataset the first thing done is determining te size of the file. This is done in the `_info` method withn the http module of fsspec.

```python
    async def _info(self, url, **kwargs):
        """Get info of URL

        Tries to access location via HEAD, and then GET methods, but does
        not fetch the data.

        It is possible that the server does not supply any size information, in
        which case size will be given as None (and certain operations on the
        corresponding file will not work).
        """
        size = False
        kw = self.kwargs.copy()
        kw.update(kwargs)
        for policy in ["head", "get"]:
            try:
                session = await self.set_session()
                size = await _file_size(url, size_policy=policy, session=session, **kw)
                if size:
                    break
            except Exception as e:
                logger.debug((str(e)))
        else:
            # get failed, so conclude URL does not exist
            if size is False:
                raise FileNotFoundError(url)
        return {"name": url, "size": size or None, "type": "file"}
```

the `_file_size` method does this:
```python
async def _file_size(url, session=None, size_policy="head", **kwargs):
    """Call HEAD on the server to get file size

    Default operation is to explicitly allow redirects and use encoding
    'identity' (no compression) to get the true size of the target.
    """
    logger.debug("Retrieve file size for %s" % url)
    kwargs = kwargs.copy()
    ar = kwargs.pop("allow_redirects", True)
    head = kwargs.get("headers", {}).copy()
    head["Accept-Encoding"] = "identity"
    kwargs["headers"] = head
    session = session or await get_client()
    if size_policy == "head":
        r = await session.head(url, allow_redirects=ar, **kwargs)
    elif size_policy == "get":
        r = await session.get(url, allow_redirects=ar, **kwargs)
    else:
        raise TypeError('size_policy must be "head" or "get", got %s' "" % size_policy)
    async with r:
        # TODO:
        #  recognise lack of 'Accept-Ranges', or  'Accept-Ranges': 'none' (not 'bytes')
        #  to mean streaming only, no random access => return None
        if "Content-Length" in r.headers:
            return int(r.headers["Content-Length"])
        elif "Content-Range" in r.headers:
            return int(r.headers["Content-Range"].split("/")[1])
        r.close()
```

this results in the following request:
```json
    "httpRequest": {
      "path": "/demo-s3-output/output/data/demo/spark/cars-all/part-00000-7512f0aa-e860-483c-aea5-e6bb2dd493ac-c000.snappy.parquet",
      "method": "HEAD",
      "queryStringParameters": [
        ...
      ]
    }
```

with response:
```json
    "httpResponse": {
      "body": "Error validating signature",
      "statusCode": 403,
      "headers": {
        "Content-Length": [ "123" ],
        "Content-Type": [ "text/plain" ]
      }
    }
```

Because there is no responsestatus check in the `_file_size` method the Content-Length of the error is taken as the file size.

The reason for the 403 status is that the url signing takes the method into account when signing and the signing was based on the GET method instead of the HEAD method.

### Running the setup

```bash
docker-compose up --build --force-recreate
```
