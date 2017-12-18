#!/usr/bin/env python

import argparse
import glob
import os
import tempfile
from os.path import basename, dirname, exists, splitext
from os.path import join as pjoin
from subprocess import check_call

import h5py
import numpy as np
import yaml
from gaip.acquisition import acquisitions
from gaip.data import write_img
from gaip.geobox import GriddedGeoBox
from gaip.hdf5 import find
from pkg_resources import resource_stream
from rasterio.enums import Resampling
from yaml.representer import Representer

import s2pkg
from s2pkg.checksum import checksum
from s2pkg.contiguity import do_contiguity
from s2pkg.contrast import quicklook
from s2pkg.fmask_cophub import fmask_cogtif
from s2pkg.html_geojson import html_map
from s2pkg.yaml_merge import merge_metadata

yaml.add_representer(np.int8, Representer.represent_int)
yaml.add_representer(np.uint8, Representer.represent_int)
yaml.add_representer(np.int16, Representer.represent_int)
yaml.add_representer(np.uint16, Representer.represent_int)
yaml.add_representer(np.int32, Representer.represent_int)
yaml.add_representer(np.uint32, Representer.represent_int)
yaml.add_representer(int, Representer.represent_int)
yaml.add_representer(np.int64, Representer.represent_int)
yaml.add_representer(np.uint64, Representer.represent_int)
yaml.add_representer(float, Representer.represent_float)
yaml.add_representer(np.float32, Representer.represent_float)
yaml.add_representer(np.float64, Representer.represent_float)
yaml.add_representer(np.ndarray, Representer.represent_list)

PRODUCTS = ['NBAR', 'NBART']
LEVELS = [2, 4, 8, 16, 32]


def run_command(command, work_dir):
    """A simple utility to execute a subprocess command."""
    check_call(command, cwd=work_dir)


def gaip_unpack(scene, granule, h5group, outdir):
    """Unpack and package the NBAR and NBART products."""
    # listing of all datasets of IMAGE CLASS type
    img_paths = find(h5group, 'IMAGE')

    for product in PRODUCTS:
        for pathname in [p for p in img_paths if f'/{product}/' in p]:

            dataset = h5group[pathname]
            if dataset.attrs['band_name'] == 'BAND-9':
                continue

            acqs = scene.get_acquisitions(group=pathname.split('/')[0],
                                          granule=granule)
            acq = [a for a in acqs if
                   a.band_name == dataset.attrs['band_name']][0]

            # base_dir = pjoin(splitext(basename(acq.pathname))[0], granule)
            base_fname = f'{splitext(basename(acq.uri))[0]}.TIF'
            out_fname = pjoin(outdir,
                              # base_dir.replace('L1C', 'ARD'),
                              # granule.replace('L1C', 'ARD'),
                              product,
                              base_fname.replace('L1C', product))

            # output
            if not exists(dirname(out_fname)):
                os.makedirs(dirname(out_fname))

            write_img(dataset, out_fname, cogtif=True, levels=LEVELS,
                      nodata=dataset.attrs['no_data_value'],
                      geobox=GriddedGeoBox.from_dataset(dataset),
                      resampling=Resampling.nearest,
                      options={'blockxsize': dataset.chunks[1],
                               'blockysize': dataset.chunks[0],
                               'compress': 'deflate',
                               'zlevel': 4})

    # retrieve metadata
    scalar_paths = find(h5group, 'SCALAR')
    pathname = [pth for pth in scalar_paths if 'NBAR-METADATA' in pth][0]
    tags = yaml.load(h5group[pathname][()])
    return tags


def build_vrts(outdir):
    """Build the various vrt's."""
    exe = 'gdalbuildvrt'

    for product in PRODUCTS:
        out_path = pjoin(outdir, product)
        expr = pjoin(out_path, '*_B02.TIF')
        base_name = basename(glob.glob(expr)[0]).replace('B02.TIF', '')

        out_fname = f'{base_name}ALLBANDS_20m.vrt'
        cmd = [exe,
               '-resolution',
               'user',
               '-tr',
               '20',
               '20',
               '-separate',
               '-overwrite',
               out_fname,
               '*_B0[1-8].TIF',
               '*_B8A.TIF',
               '*_B1[1-2].TIF']
        run_command(cmd, out_path)

        out_fname = f'{base_name}10m.vrt'
        cmd = [exe,
               '-separate',
               '-overwrite',
               out_fname,
               '*_B0[2-48].TIF']
        run_command(cmd, out_path)

        out_fname = f'{base_name}20m.vrt'
        cmd = [exe,
               '-separate',
               '-overwrite',
               out_fname,
               '*_B0[5-7].TIF',
               '*_B8A.TIF',
               '*_B1[1-2].TIF']
        run_command(cmd, out_path)

        out_fname = f'{base_name}60m.vrt'
        cmd = [exe,
               '-separate',
               '-overwrite',
               out_fname,
               '*_B01.TIF']
        run_command(cmd, out_path)


def create_contiguity(outdir):
    """Create the contiguity dataset for each."""
    for product in PRODUCTS:
        out_path = pjoin(outdir, product)
        expr = pjoin(out_path, '*ALLBANDS_20m.vrt')
        fname = glob.glob(expr)[0]
        out_fname = fname.replace('.vrt', '_CONTIGUITY.TIF')

        # create contiguity
        do_contiguity(fname, out_fname)


def create_html_map(outdir):
    """Create the html map and GeoJSON valid data extents files."""
    expr = pjoin(outdir, 'NBAR', '*_CONTIGUITY.TIF')
    contiguity_fname = glob.glob(expr)[0]
    html_fname = pjoin(outdir, 'map.html')
    json_fname = pjoin(outdir, 'bounds.geojson')

    # html valid data extents
    html_map(contiguity_fname, html_fname, json_fname)


def create_quicklook(outdir):
    """Create the quicklook and thumbnail images."""
    for product in PRODUCTS:
        out_path = pjoin(outdir, product)
        fname = glob.glob(pjoin(out_path, '*10m.vrt'))[0]
        out_fname1 = fname.replace('10m.vrt', 'QUICKLOOK.TIF')
        out_fname2 = fname.replace('10m.vrt', 'THUMBNAIL.TIF')

        with tempfile.TemporaryDirectory(dir=out_path,
                                         prefix='quicklook-') as tmpdir:

            tmp_fname1 = pjoin(tmpdir, 'tmp1.tif')
            tmp_fname2 = pjoin(tmpdir, 'tmp2.tif')
            quicklook(fname, out_fname=tmp_fname1, src_min=1, src_max=3500,
                      out_min=1)

            # warp to Lon/Lat WGS84
            cmd = ['gdalwarp',
                   '-t_srs',
                   '"EPSG:4326"',
                   '-tap',
                   '-tap',
                   '-co',
                   'COMPRESS=JPEG',
                   '-co',
                   'PHOTOMETRIC=YCBCR',
                   '-co',
                   'TILED=YES'
                   '-tr',
                   '0.0001',
                   '0.0001',
                   tmp_fname1,
                   tmp_fname2]
            run_command(cmd, out_path)

            # build overviews/pyramids
            cmd = ['gdaladdo',
                   '-r',
                   'average',
                   tmp_fname2,
                   '2',
                   '4',
                   '8',
                   '16',
                   '32']
            run_command(cmd, out_path)

            # create the cogtif
            cmd = ['gdal_translate',
                   '-co',
                   'TILED=YES',
                   '-co',
                   'COPY_SRC_OVERVIEWS=YES',
                   '-co',
                   'COMPRESS=JPEG',
                   '-co',
                   'PHOTOMETRIC=YCBCR',
                   tmp_fname2,
                   out_fname1]
            run_command(cmd, out_path)

            # create the thumbnail
            cmd = ['gdal_translate',
                   '-of',
                   'JPEG',
                   '-outsize',
                   '10%',
                   '10%',
                   out_fname1,
                   out_fname2]
            run_command(cmd, out_path)


def create_readme(outdir):
    """Create the readme file."""
    with resource_stream(s2pkg.__name__, '_README') as src:
        with open(pjoin(outdir, 'README'), 'w') as out_src:
            out_src.writelines([l.decode('utf-8') for l in src.readlines()])


def create_checksum(outdir):
    """Create the checksum file."""
    out_fname = pjoin(outdir, 'CHECKSUM.sha1')
    checksum(out_fname)


def package(l1_path, gaip_fname, fmask_path, yamls_path, outdir):
    """Main level."""
    scene = acquisitions(l1_path)
    with open(pjoin(yamls_path, f'{scene.label}.yaml')) as src:
        l1_documents = {doc['tile_id']: doc for doc in yaml.load_all(src)}

    with h5py.File(gaip_fname, 'r') as fid:
        for granule in scene.granules:
            if granule is None:
                h5group = fid['/']
            else:
                h5group = fid[granule]

            ard_granule = granule.replace('L1C', 'ARD')
            out_path = pjoin(outdir, ard_granule)

            # fmask cogtif conversion
            fmask_cogtif(pjoin(fmask_path, f'{granule}.cloud.img'),
                         pjoin(out_path, f'{ard_granule}_QA.TIF'))

            # unpack the data produced by gaip
            gaip_tags = gaip_unpack(scene, granule, h5group, out_path)

            # merge all the yaml documents
            tags = merge_metadata(l1_documents[granule], gaip_tags, out_path)

            with open(pjoin(out_path, 'ARD-METADATA.yaml'), 'w') as src:
                yaml.dump(tags, src, default_flow_style=False, indent=4)

            # vrts, contiguity, map, quicklook, thumbnail, readme, checksum
            build_vrts(out_path)
            create_contiguity(out_path)
            create_html_map(out_path)
            create_quicklook(out_path)
            create_readme(out_path)
            create_checksum(out_path)


if __name__ == '__main__':
    description = "Prepare or package a gaip output."
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("--level1-pathname", required=True,
                        help="The level1 pathname.")
    parser.add_argument("--gaip-filename", required=True,
                        help="The filename of the gaip output.")
    parser.add_argument("--fmask-pathname", required=True,
                        help=("The pathname to the directory containing the "
                              "fmask results for the level1 dataset."))
    parser.add_argument("--prepare-yamls", required=True,
                        help="The pathname to the level1 prepare yamls.")
    parser.add_argument("--outdir", required=True,
                        help="The output directory.")

    args = parser.parse_args()

    package(args.level1_pathname, args.gaip_filename, args.fmask_pathname,
            args.prepare_yamls, args.outdir)
