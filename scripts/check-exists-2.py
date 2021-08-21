from pathlib import Path
from datetime import datetime

import luigi
import click
import yaml

import boto3
from botocore.exceptions import ClientError

import eodatasets3


def check_object_exists(s3_bucket, key):
    s3 = boto3.client('s3')
    print('checking for output at', s3_bucket, key)

    try:
        obj = s3.head_object(Bucket=s3_bucket, Key=key)
        print('output already exists')
        return True

    except ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise
        print('output does not exist yet')
        return False


def get_luigi_config_params():
    config = luigi.configuration.get_config()

    result = {}

    maturity = config.get('Package', 'product_maturity', 'stable')
    if maturity != 'stable':
        result['dea:product_maturity'] = maturity
    }


def convert_to_l2(properties):
    result = dict(properties)

    result['odc:processing_datetime'] = datetime.utcnow()
    result['odc:product_family'] = 'ard'
    result['odc:producer'] = 'ga.gov.au'
    result['odc:dataset_version'] = '3.2.1'


def target_metadata_doc(properties, collection_prefix):
    if 'sentinel' in properties['eo:platform']:
        conventions = 'dea_s2'
    else:
        convensions = 'dea'

    names = eodatasets3.namer(properties, collection_prefix=collection_prefix, conventions=conventions)

    return names.dataset_location + '/' + names.metadata_file


@click.command()
@click.option('--level1-path', required=True)
@click.option('--s3-bucket', required=True)
@click.option('--s3-prefix', required=True)
def main(level1_path, s3_bucket, s3_prefix):
    [metadata_doc] = Path(level1_path).rglob('*.odc-metadata.yaml')

    with open(metadata_doc) as fl:
        level1_doc = yaml.load(fl, Loader=yaml.SafeLoader)

    properties = {**level1_doc['properties'], **get_luigi_config_params()}

    metadata_doc = target_metadata_doc(properties, '').lstrip('/')

    print('metadata_doc', metadata_doc)
    if check_object_exists(s3_bucket, s3_prefix + metadata_doc):
        sys.exit(-1)


if __name__ == '__main__':
    main()
