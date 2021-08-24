#!/usr/bin/env python
import sys
from pathlib import Path
from datetime import datetime

import luigi
import click
import yaml

import boto3
from botocore.exceptions import ClientError

import eodatasets3


def check_object_exists(bucket, key):
    s3 = boto3.client('s3')

    try:
        obj = s3.head_object(Bucket=bucket, Key=key)
        return True

    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
        return False


def get_luigi_config_params():
    config = luigi.configuration.get_config()

    result = {}

    maturity = config.get('Package', 'product_maturity', 'stable')
    if maturity != 'stable':
        result['dea:product_maturity'] = maturity

    return result


def convert_to_l2(properties):
    result = dict(properties)

    result['odc:processing_datetime'] = datetime.utcnow()
    result['odc:product_family'] = 'ard'
    result['odc:producer'] = 'ga.gov.au'
    result['odc:dataset_version'] = '3.2.1'
    result['dea:dataset_maturity'] = 'nrt'

    return result


def target_metadata_doc(properties, collection_prefix):
    if 'sentinel' in properties['eo:platform']:
        conventions = 'dea_s2'
    else:
        conventions = 'dea'

    names = eodatasets3.namer(properties, collection_prefix=collection_prefix, conventions=conventions)

    return names.resolve_file(names.metadata_file)


@click.command()
@click.option('--level1-path', required=True)
@click.option('--s3-bucket', required=True)
@click.option('--s3-prefix', required=True)
def main(level1_path, s3_bucket, s3_prefix):
    [metadata_file] = Path(level1_path).rglob('*.odc-metadata.yaml')

    print('level1 metadata file', metadata_file)
    with open(metadata_file) as fl:
        level1_doc = yaml.load(fl, Loader=yaml.SafeLoader)

    properties = {**level1_doc['properties'], **get_luigi_config_params()}

    print('level1 properties')
    print(yaml.dump(properties, indent=4))

    properties = convert_to_l2(properties)
    print('level2 properties')
    print(yaml.dump(properties, indent=4))

    prefix = f's3://{s3_bucket}/{s3_prefix}'.rstrip('/')
    dataset_location = target_metadata_doc(properties, prefix)
    print('metadata location', dataset_location)

    key = dataset_location[len(f"s3://{s3_bucket}/"):]
    print('checking for output at', s3_bucket, key)
    if check_object_exists(s3_bucket, key):
        print('output already exists')
        sys.exit(-1)

    print('output does not exist yet')


if __name__ == '__main__':
    main()
