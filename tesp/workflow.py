#!/usr/bin/env python

"""A temporary workflow for processing S2 data into an ARD package."""

import logging
import re
import shutil
import traceback
from os.path import basename
from os.path import join as pjoin
from pathlib import Path
from posixpath import join as ppjoin

import luigi
from eugl.fmask import fmask
from luigi.contrib.s3 import S3Client, S3FlagTarget
from luigi.local_target import LocalFileSystem
from luigi.util import inherits
from structlog import wrap_logger
from structlog.processors import JSONRenderer

# Note that utilising the luigi.contrib.s3 module requires boto to be installed
# This affects the PackageS3 and ARDPS3 Tasks
from wagl.acquisition import acquisitions
from wagl.singlefile_workflow import DataStandardisation

from tesp.package import ARD, PATTERN2, package

ERROR_LOGGER = wrap_logger(
    logging.getLogger("ard-error"), processors=[JSONRenderer(indent=1, sort_keys=True)]
)
INTERFACE_LOGGER = logging.getLogger("luigi-interface")


@luigi.Task.event_handler(luigi.Event.FAILURE)
def on_failure(task, exception):
    """Capture any Task Failure here."""
    ERROR_LOGGER.error(
        task=task.get_task_family(),
        params=task.to_str_params(),
        level1=getattr(task, "level1", ""),
        exception=exception.__str__(),
        traceback=traceback.format_exc().splitlines(),
    )


class WorkDir(luigi.Task):
    """Initialises the working directory in a controlled manner.
    Alternatively this could be initialised upfront during the
    ARD Task submission phase.
    """

    level1 = luigi.Parameter()
    workdir = luigi.Parameter()

    def output(self):
        return luigi.LocalTarget(self.workdir)

    def run(self):
        local_fs = LocalFileSystem()
        local_fs.mkdir(self.output().path)


class RunFmask(luigi.Task):
    """Execute the Fmask algorithm for a given granule."""

    level1 = luigi.Parameter()
    granule = luigi.Parameter()
    workdir = luigi.Parameter()
    acq_parser_hint = luigi.Parameter(default=None)

    def requires(self):
        # for the time being have fmask require wagl,
        # no point in running fmask if wagl fails...
        # return WorkDir(self.level1, dirname(self.workdir))
        return DataStandardisation(self.level1, self.workdir, self.granule)

    def output(self):
        out_fname = pjoin(self.workdir, f"{self.granule}.fmask.img")

        return luigi.LocalTarget(out_fname)

    def run(self):
        with self.output().temporary_path() as out_fname:
            fmask(
                self.level1, self.granule, out_fname, self.workdir, self.acq_parser_hint
            )


# useful for testing fmask via the CLI
class Fmask(luigi.WrapperTask):
    """A helper task that issues RunFmask Tasks."""

    level1 = luigi.Parameter()
    workdir = luigi.Parameter()
    acq_parser_hint = luigi.Parameter(default=None)

    def requires(self):
        # issues task per granule
        container = acquisitions(self.level1, self.acq_parser_hint)
        for granule in container.granules:
            yield RunFmask(self.level1, granule, self.workdir)


# TODO: GQA implementation
# class Gqa(luigi.Task):

#     level1 = luigi.Parameter()
#     outdir = luigi.Parameter()


class Package(luigi.Task):
    """Creates the final packaged product once wagl, Fmask
    and gqa have executed successfully.
    """

    level1 = luigi.Parameter()
    workdir = luigi.Parameter()
    granule = luigi.Parameter(default=None)
    pkgdir = luigi.Parameter()
    url_root = luigi.Parameter()
    yamls_dir = luigi.Parameter()
    cleanup = luigi.BoolParameter()
    acq_parser_hint = luigi.Parameter(default=None)

    def requires(self):
        tasks = {
            "wagl": DataStandardisation(self.level1, self.workdir, self.granule),
            "fmask": RunFmask(self.level1, self.granule, self.workdir),
        }
        # TODO: GQA implementation
        # 'gqa': Gqa()}

        return tasks

    def output(self):
        granule = re.sub(PATTERN2, ARD, self.granule)
        out_fname = pjoin(self.pkgdir, granule, "CHECKSUM.sha1")

        return luigi.LocalTarget(out_fname)

    def run(self):
        inputs = self.input()
        package(
            self.level1,
            inputs["wagl"].path,
            inputs["fmask"].path,
            self.yamls_dir,
            self.pkgdir,
            self.url_root,
            self.granule,
            self.acq_parser_hint,
        )

        if self.cleanup:
            shutil.rmtree(self.workdir)


class ARDP(luigi.WrapperTask):
    """A helper Task that issues Package Tasks for each Level-1
    dataset listed in the `level1_list` parameter.
    """

    level1_list = luigi.Parameter()
    workdir = luigi.Parameter()
    pkgdir = luigi.Parameter()
    url_root = luigi.Parameter()
    acq_parser_hint = luigi.Parameter(default=None)

    def requires(self):
        with open(self.level1_list) as src:
            level1_list = [level1.strip() for level1 in src.readlines()]

        for level1 in level1_list:
            work_root = pjoin(self.workdir, f"{basename(level1)}.ARD")
            container = acquisitions(level1, self.acq_parser_hint)
            for granule in container.granules:
                work_dir = container.get_root(work_root, granule=granule)
                acq = container.get_acquisitions(None, granule, False)[0]
                ymd = acq.acquisition_datetime.strftime("%Y-%m-%d")
                pkgdir = pjoin(self.pkgdir, ymd)
                url_root = pjoin(self.url_root, ymd)
                yield Package(level1, work_dir, granule, pkgdir, url_root)


@inherits(Package)
class PackageS3(luigi.Task):
    """Uploads the packaged data to an s3_bucket and prefix after running the
    Package task successfully.
    s3_bucket and s3_prefix_key are used for the destination path,
    s3_bucket_region is used to resolve s3_root for the S3-ARD.yml.
    """

    s3_bucket = luigi.Parameter()
    s3_key_prefix = luigi.Parameter()
    s3_bucket_region = luigi.Parameter()
    s3_object_base_tags = luigi.DictParameter(default={}, significant=False)

    MEDIA_TYPES = {
        "geojson": "application/geo+json",
        "htm": "text/html",
        "html": "text/html",
        "jpg": "image/jpeg",
        "sha1": "text/plain",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "vrt": "text/xml",
        "xml": "text/xml",
        "yaml": "text/plain",
        "yml": "text/plain",
        "md": "text/plain",
    }

    def requires(self):
        url_root = "http://{}.s3-{}.amazonaws.com/{}".format(
            self.s3_bucket, self.s3_bucket_region, self.s3_key_prefix
        )
        return Package(self.level1, self.workdir, self.granule, self.pkgdir, url_root)

    def output(self):
        # Assumes that the flag file is at the root of the package
        resolved_checksum = Path(self.input().path).resolve()
        return S3FlagTarget(
            f"s3://{self.s3_bucket}/{self.s3_key_prefix}/"
            + resolved_checksum.parent.name
            + "/",
            flag=resolved_checksum.name,
        )

    def run(self):
        s3_client = S3Client()
        http_header_tags = "&".join(
            [f"{k}={v}" for k, v in self.s3_object_base_tags.items()]
        )

        granule = Path(self.input().path).resolve().parent
        granule_prefix_len = len(granule.parent.as_posix())
        for path in granule.rglob("*"):
            if path.is_dir():
                continue

            s3_client.put_multipart(
                path,
                f"s3://{self.s3_bucket}/{self.s3_key_prefix}"
                + path.as_posix()[granule_prefix_len:],  # relative path inc. granule_id
                headers={
                    "Content-Type": self._get_content_mediatype(path),
                    "x-amz-tagging": http_header_tags,
                },
            )

    @classmethod
    def _get_content_mediatype(cls, path):
        # Special case, README files don't have a suffix
        if path.stem == "README":
            return "text/plain"

        return cls.MEDIA_TYPES.get(
            str(path.suffix)[1:].lower(), "application/octet-stream"
        )


@inherits(ARDP)
class ARDPS3(luigi.WrapperTask):
    """A helper Task that issues PackageS3 tasks for each Level-1
    dataset listed in the `level1_list` parameter.
    """

    s3_bucket = luigi.Parameter()
    s3_key_prefix = luigi.Parameter()
    s3_bucket_region = luigi.Parameter()

    def requires(self):
        with open(self.level1_list) as src:
            level1_list = [level1.strip() for level1 in src.readlines()]

        for level1 in level1_list:
            work_root = pjoin(self.workdir, f"{basename(level1)}.ARD")
            container = acquisitions(level1, self.acq_parser_hint)
            for granule in container.granules:
                work_dir = container.get_root(work_root, granule=granule)
                acq = container.get_acquisitions(None, granule, False)[0]
                ymd = acq.acquisition_datetime.strftime("%Y-%m-%d")
                pkgdir = pjoin(self.pkgdir, ymd)
                yield PackageS3(
                    level1,
                    work_dir,
                    granule,
                    pkgdir,
                    s3_bucket=self.s3_bucket,
                    s3_key_prefix=ppjoin(self.s3_key_prefix, ymd),
                    s3_bucket_region=self.s3_bucket_region,
                )


if __name__ == "__main__":
    luigi.run()
