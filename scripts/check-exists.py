import click
import sys
from pathlib import Path
from posixpath import join as ppjoin

import boto3
from botocore.exceptions import ClientError

from wagl.acquisition import acquisitions
from tesp.workflow import Package

@click.command()
@click.option('--level1-path', required=True)
@click.option('--s3-bucket', required=True)
@click.option('--s3-prefix', required=True)
@click.option('--acq-parser-hint', required=False)
def main(level1_path, s3_bucket, s3_prefix, acq_parser_hint):
    container = acquisitions(level1_path, hint=acq_parser_hint)
    [granule] = container.granules
    acq = container.get_acquisitions(None, granule, False)[0]
    ymd = acq.acquisition_datetime.strftime('%Y-%m-%d')
    package = Package('', '', granule, ppjoin(s3_prefix, ymd), '', acq_parser_hint='')

    s3 = boto3.client('s3')
    key = package.output().path
    print('checking for output at', s3_bucket, key)

    try:
        obj = s3.head_object(Bucket=s3_bucket, Key=key)
        print('output already exists')
        sys.exit(-1)

    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
        print('output does not exist yet')


if __name__ == '__main__':
    main()
