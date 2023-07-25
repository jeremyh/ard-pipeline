import sys
from posixpath import join as ppjoin

import boto3
import click
from botocore.exceptions import ClientError

from tesp.workflow import Package
from wagl.acquisition import acquisitions


@click.command()
@click.option("--level1-path", required=True)
@click.option("--acq-parser-hint", required=True)
@click.option("--s3-bucket", required=True)
@click.option("--s3-prefix", required=True)
def main(level1_path, acq_parser_hint, s3_bucket, s3_prefix):
    container = acquisitions(level1_path, hint=acq_parser_hint)
    [granule] = container.granules
    acq = container.get_acquisitions(None, granule, False)[0]
    ymd = acq.acquisition_datetime.strftime("%Y-%m-%d")
    package = Package("", "", granule, ppjoin(s3_prefix, ymd), "", acq_parser_hint="")

    s3 = boto3.client("s3")
    key = package.output().path

    try:
        s3.head_object(Bucket=s3_bucket, Key=key)
        print("output already exists")
        sys.exit(-1)

    except ClientError as e:
        if e.response["Error"]["Code"] != "404":
            raise
        print("output does not exist yet")


if __name__ == "__main__":
    main()
