"""MODTRAN drivers
---------------.

"""
import os
import subprocess
from os.path import abspath, dirname, exists
from os.path import join as pjoin

import gaip

BIN_DIR = abspath(pjoin(dirname(__file__), "..", "bin"))


def create_modtran_dirs(
    coords, albedos, modtran_root, modtran_exe_root, workpath_format, input_format
):
    """Create all modtran subdirectories. and input files."""
    if not exists(modtran_root):
        os.makedirs(modtran_root)

    data_dir = pjoin(modtran_exe_root, "DATA")
    if not exists(data_dir):
        raise OSError("Cannot find MODTRAN")

    for coord in coords:
        for albedo in albedos:
            modtran_work = workpath_format.format(coord=coord, albedo=albedo)
            modtran_work = pjoin(modtran_root, modtran_work)
            mod5root_in = input_format.format(coord=coord, albedo=albedo)
            mod5root_in = pjoin(modtran_root, mod5root_in)

            if not exists(modtran_work):
                os.makedirs(modtran_work)

            with open(mod5root_in, "w") as outfile:
                outfile.write(coord + "_alb_" + albedo + "\n")

            symlink_dir = pjoin(modtran_work, "DATA")
            if exists(symlink_dir):
                os.unlink(symlink_dir)

            os.symlink(data_dir, symlink_dir)


def create_satellite_filter_file(acquisitions, satfilter_path, target):
    """Generate satellite filter input file."""
    refbands = [a for a in acquisitions if a.band_type == gaip.REF]
    filterfile = acquisitions[0].spectral_filter_file
    filterpath = os.path.join(satfilter_path, filterfile)

    with open(target, "w") as outfile:
        outfile.write("%i\n" % len(refbands))
        outfile.write("%s\n" % filterpath)

    return target


def write_modtran_input(
    acquisitions, modtran_input_file, ozone, vapour, aerosol, elevation
):
    """Generate modtran input file."""
    acq = acquisitions[0]
    filter_file = acq.spectral_filter_file
    cdate = acq.scene_centre_date
    altitude = acq.altitude / 1000.0  # in km
    dechour = acq.decimal_hour

    with open(modtran_input_file, "w") as outfile:
        outfile.write("%f\n" % ozone)
        outfile.write("%f\n" % vapour)
        outfile.write("DATA/%s\n" % filter_file)
        outfile.write("-%f\n" % aerosol)
        outfile.write("%f\n" % elevation)
        outfile.write("Annotation, %s\n" % cdate.strftime("%Y-%m-%d"))
        outfile.write("%d\n" % altitude)
        outfile.write("%d\n" % int(cdate.strftime("%j")))
        outfile.write("%f\n" % dechour)


def write_modis_brdf_files(
    acquisitions, fname_format, brdf_data, solar_irrad_data, solar_dist_data
):
    """Generate brdf input file."""
    ref_acqs = [a for a in acquisitions if a.band_type == gaip.REF]

    for acq in ref_acqs:
        band = acq.band_num
        modis_brdf_filename = fname_format.format(band_num=band)
        with open(modis_brdf_filename, "w") as outfile:
            msg = "{iso} {vol} {geo}\n"
            msg = msg.format(
                iso=brdf_data[(band, "iso")]["value"],
                vol=brdf_data[(band, "vol")]["value"],
                geo=brdf_data[(band, "geo")]["value"],
            )
            outfile.write(msg)

            msg = "{bias} {gain} {irrad} {dist}\n"
            msg = msg.format(
                bias=acq.bias,
                gain=acq.gain,
                irrad=solar_irrad_data[band],
                dist=solar_dist_data["distance"],
            )
            outfile.write(msg)


def run_box_line_coordinates(centreline, sat_view_zenith, coordinator, boxline, cwd):
    """Run box_line_coordinates executable."""
    cmd = pjoin(BIN_DIR, "box_line_coordinates")

    args = [cmd, centreline, sat_view_zenith, coordinator, boxline]

    subprocess.check_call(args)


def generate_modtran_inputs(
    modtran_input,
    coordinator,
    sat_view_zenith,
    sat_azimuth,
    lon_grid,
    lat_grid,
    coords,
    albedos,
    fname_format,
    workdir,
):
    """Generate MODTRAN input files."""
    cmd = pjoin(BIN_DIR, "generate_modtran_input")

    args = [
        cmd,
        modtran_input,
        coordinator,
        sat_view_zenith,
        sat_azimuth,
        lat_grid,
        lon_grid,
    ]

    targets = []
    for coord in coords:
        for albedo in albedos:
            target = fname_format.format(coord=coord, albedo=albedo)
            targets.append(pjoin(workdir, target))

    args.extend(targets)

    subprocess.check_call(args)

    return targets


def reformat_as_tp5(
    coords,
    albedos,
    profile,
    input_format,
    output_format,
    workdir,
    cmd=pjoin(BIN_DIR, "reformat_tp5_albedo"),
):
    """Reformat the MODTRAN input files in `tp5` format."""
    targets = []
    for coord in coords:
        for albedo in albedos:
            src = input_format.format(coord=coord, albedo=albedo)
            dst = output_format.format(coord=coord, albedo=albedo)
            targets.append(pjoin(workdir, dst))

            args = [cmd, pjoin(workdir, src), profile, pjoin(workdir, dst)]

            subprocess.check_call(args)

    return targets


def reformat_as_tp5_trans(
    coords, albedos, profile, input_format, output_format, workdir
):
    """Reformat the MODTRAN input files in `tp5` format in the trans case."""
    cmd = pjoin(BIN_DIR, "reformat_tp5_transmittance")
    return reformat_as_tp5(
        coords, albedos, profile, input_format, output_format, workdir, cmd
    )


def run_modtran(modtran_exe, workpath):
    """Run MODTRAN."""
    subprocess.check_call([modtran_exe], cwd=workpath)


def extract_flux(coords, albedos, input_format, output_format, satfilter):
    """Extract the flux data."""
    cmd = pjoin(BIN_DIR, "read_flux_albedo")

    for coord in coords:
        for albedo in albedos:
            src = input_format.format(coord=coord, albedo=albedo)
            dst = output_format.format(coord=coord, albedo=albedo)
            args = [cmd, src, satfilter, dst]

            subprocess.check_call(args)


def extract_flux_trans(coords, input_format, output_format, satfilter):
    """Extract the flux data in the transmissive case."""
    cmd = pjoin(BIN_DIR, "read_flux_transmittance")

    for coord in coords:
        src = input_format.format(coord=coord)
        dst = output_format.format(coord=coord)
        args = [cmd, src, satfilter, dst]

        subprocess.check_call(args)


def calc_coefficients(coords, chn_input_fmt, dir_input_fmt, output_fmt, satfilter, cwd):
    """Calculate the coefficients from the MODTRAN output."""
    cmd = pjoin(BIN_DIR, "calculate_coefficients")

    for coord in coords:
        args = [
            cmd,
            satfilter,
            pjoin(cwd, chn_input_fmt.format(coord=coord, albedo=0)),
            pjoin(cwd, chn_input_fmt.format(coord=coord, albedo=1)),
            pjoin(cwd, dir_input_fmt.format(coord=coord, albedo=0)),
            pjoin(cwd, dir_input_fmt.format(coord=coord, albedo=1)),
            pjoin(cwd, dir_input_fmt.format(coord=coord, albedo="t")),
            pjoin(cwd, output_fmt.format(coord=coord)),
        ]

        subprocess.check_call(args, cwd=cwd)


def reformat_atmo_params(
    acqs, coords, satfilter, factors, input_fmt, output_fmt, workpath
):
    """Reformat atmospheric parameters."""
    cmd = pjoin(BIN_DIR, "reformat_modtran_output")

    bands = [str(a.band_num) for a in acqs]

    args = [cmd, satfilter]
    for coord in coords:
        args.append(input_fmt.format(coord=coord))

    for band in bands:
        for factor in factors:
            args.append(output_fmt.format(factor=factor, band=band))

    subprocess.check_call(args, cwd=workpath)


def bilinear_interpolate(
    acqs, factors, coordinator, boxline, centreline, input_fmt, output_fmt, workpath
):
    """Perform bilinear interpolation."""
    cmd = pjoin(BIN_DIR, "bilinear_interpolation")

    bands = [a.band_num for a in acqs]

    # Initialise the dict to store the locations of the bilinear outputs
    bilinear_outputs = {}

    # Base ENVI header file
    hdr = (
        "ENVI\n"
        "samples = {samples}\n"
        "lines   = {lines}\n"
        "bands   = 1\n"
        "data type = 4\n"
        "interleave = bsq"
        "byte order = 0"
    ).format(samples=acqs[0].samples, lines=acqs[0].lines)

    for band in bands:
        for factor in factors:
            fname = output_fmt.format(factor=factor, band=band)
            fname = pjoin(workpath, fname)
            hdr_fname = fname.replace(".bin", ".hdr")
            with open(hdr_fname, "w") as outf:
                for line in hdr:
                    outf.write(line)
            bilinear_outputs[(band, factor)] = fname
            args = [
                cmd,
                coordinator,
                input_fmt.format(factor=factor, band=band),
                boxline,
                centreline,
                fname,
            ]

            subprocess.check_call(args, cwd=workpath)

    return bilinear_outputs
