#!/usr/bin/env python

"""PBS submission scripts."""

import json
import logging
import math
import os
import re
import subprocess
import uuid
from os.path import dirname, exists
from os.path import join as pjoin
from pathlib import Path
from typing import Optional, Set, Union

import click

from wagl.tiling import scatter

PBS_RESOURCES = """#!/bin/bash
#PBS -P {project}
#PBS -W umask=017
#PBS -q {queue}
#PBS -l walltime={walltime},mem={memory}GB,ncpus={ncpus},jobfs={jobfs}GB,other=pernodejobfs
#PBS -l wd
#PBS -l storage={filesystem_projects}
#PBS -me
{email}
"""

NODE_TEMPLATE = """{pbs_resources}
source {env}

{daemon}

luigi --module tesp.workflow ARDP --level1-list {scene_list} --workdir {outdir} --pkgdir {pkgdir} --yamls-dir="{yamls_dir}" --workers {workers} --parallel-scheduling
"""

CLEAN_UP_TEMPLATE = """
# clean up workdir since we don't need it afterwards, even if the processing has failed
rm -rf {outdir}
"""

SUMMARY_TEMPLATE = """{pbs_resources}
#PBS -W depend=afterany:{jobids}

source {env}
ard_batch_summary --indir {indir} --outdir {outdir}

# jq queries
# concatenate logs to enable querying on a single file
find -type f -name 'task-log.jsonl' | xargs cat >> batch-{batchid}-task-log.jsonl
find -type f -name 'status-log.jsonl' | xargs cat >> batch-{batchid}-status-log.jsonl

# summaries on success and failure records
jq 'select(.status == "success") | {{task, level1}}' batch-{batchid}-task-log.jsonl | jq --slurp 'unique_by(.level1, .task) | group_by(.task) | map({{task: .[0].task, count: length}})' > batch-{batchid}-success-task-summary.json
jq 'select(.status == "failure") | {{task, level1}}' batch-{batchid}-task-log.jsonl | jq --slurp 'unique_by(.level1, .task) | group_by(.task) | map({{task: .[0].task, count: length}})' > batch-{batchid}-failure-task-summary.json

# capture failures and report the exception, level1, task and granule id
jq 'select(.status == "failure") | {{level1, exception, task, granule: .params.granule}}' batch-{batchid}-task-log.jsonl | jq --slurp 'unique_by(.level1, .task, .granule)' > batch-{batchid}-exception-log.json

# get a listing of which level1-lists from which jobid's had 100% success (all scenes processed through to packaging)
jq 'select(.task == "ARDP") | {{task, level1_list: .params.level1_list, status}}' batch-{batchid}-task-log.jsonl | jq --slurp 'unique_by(.level1_list)' > batch-{batchid}-ardp-job-sucess.json

# get a listing of level1 datasets and the granule id that packaged successfully (Package is the last task to be done as defined in the luigi workflow) and report that "ard processing is complete"
jq 'select(.status == "success" and .task == "Package") | {{level1, granule: .params.granule, notification: "ard processing complete"}}' batch-{batchid}-task-log.jsonl | jq --slurp 'unique_by(.level1, .granule)' > batch-{batchid}-package-success.json

# compile a list of successfully packaged datasets (and their path) to pass over to indexing
jq 'select(.event == "packaged dataset") | .dataset_path' batch-{batchid}-status-log.jsonl | jq -sr 'unique | .[]' > batch-{batchid}-datasets-to-index.txt
"""

INDEXING_TEMPLATE = """{pbs_resources}
#PBS -W depend=afterany:{jobid}

source {env}

# indexing
cat batch-{batchid}-datasets-to-index.txt | parallel -j 47 -m -n 20 --line-buffer datacube dataset add --no-verify-lineage
"""

ARCHIVING_TEMPLATE = """{pbs_resources}

source {env}

# archiving
cat {archive_list} | parallel -j 47 -m -n 20 --line-buffer datacube dataset archive
"""


FMT1 = "batchid-{batchid}"
FMT2 = "jobid-{jobid}"
FMT3 = "level1-scenes-{jobid}.txt"
FMT4 = "jobid-{jobid}.bash"
FMT5 = "batch-{batchid}-summary.bash"
FMT6 = "batch-{batchid}-indexing.bash"
FMT7 = "scratch/{f_project}+gdata/{f_project}"
FMT8 = "archiving-{batchid}.bash"
DAEMON_FMT = "luigid --background --logdir {}"


def _calc_nodes_req(granule_count, walltime, workers, hours_per_granule=1.5):
    """Provides estimation of the number of nodes required to process granule count.

    >>> _calc_nodes_req(400, '20:59', 28)
    2
    >>> _calc_nodes_req(800, '20:00', 28)
    3
    """
    hours, _, _ = (int(x) for x in walltime.split(":"))
    return int(math.ceil(float(hours_per_granule * granule_count) / (hours * workers)))


def _get_projects_for_path(path: Path) -> Set[str]:
    """Get the NCI project used to store the given path, if any.
    >>> _get_projects_for_path(Path('/g/data/v10/some/data/path.txt'))
    {'v10'}
    >>> _get_projects_for_path(Path('/g/data4/fk4/some/data/path.txt'))
    {'fk4'}
    >>> _get_projects_for_path(Path('/scratch/da82/path.txt'))
    {'da82'}
    >>> _get_projects_for_path(Path('/tmp/other/data'))
    {None}.

    Not an automatable test, but worked locally on laptop:

    # mkdir -p /g/data/v10/some_test /g/data/rs0/other_test
    # ln -s /g/data/v10/some_test /g/data/rs0/link_to_other_test
    # >>> _get_projects_for_path(Path('/g/data/rs0/link_to_other_test'))
    # {'v10', 'rs0'}

    """

    def _immediate_project(p: Path) -> Optional[str]:
        posix_path = p.as_posix()
        if posix_path.startswith("/g/data"):
            return posix_path.split("/")[3]
        if posix_path.startswith("/scratch/"):
            return posix_path.split("/")[2]

        return None

    projects = {_immediate_project(path)}

    # If it's a symlink, there may be another project that needs to be accessible.
    physical_path = path.resolve()
    if physical_path != path:
        projects.add(_immediate_project(physical_path))

    return projects


def _filesystem_projects(
    input_paths_file: str, *other_paths: Union[str, Path]
) -> Set[str]:
    """Collect the set of projects needed by the job.

    (ie. all projects that will be touched on the filesystem, suitable
    for the `storage=` param on PBS jobs)

    """
    fs_projects = {None}

    # The current code needs to be accessible.
    fs_projects.update(_get_projects_for_path(Path(click.__file__)))

    for path in other_paths:
        if path is not None:
            fs_projects.update(_get_projects_for_path(Path(path)))

    # All input paths
    with open(input_paths_file) as src:
        paths = [p.strip() for p in src.readlines()]

    for input_path in paths:
        fs_projects.update(_get_projects_for_path(Path(input_path)))

    fs_projects.remove(None)

    return fs_projects


# pylint: disable=too-many-arguments
def _submit_multiple(
    scattered,
    env,
    batch_logdir,
    batch_outdir,
    pkgdir,
    yamls_dir,
    workers,
    pbs_resources,
    cleanup,
    test,
):
    """Submit multiple PBS formatted jobs."""
    nci_job_ids = []

    # setup and submit each block of scenes for processing
    for block in scattered:
        jobid = uuid.uuid4().hex[0:6]
        jobdir = pjoin(batch_logdir, FMT2.format(jobid=jobid))
        job_outdir = pjoin(batch_outdir, FMT2.format(jobid=jobid))

        if not exists(jobdir):
            os.makedirs(jobdir)

        if not exists(job_outdir):
            os.makedirs(job_outdir)

        # write level1 data listing
        out_fname = pjoin(jobdir, FMT3.format(jobid=jobid))
        with open(out_fname, "w") as src:
            src.writelines(block)

        pbs = NODE_TEMPLATE.format(
            pbs_resources=pbs_resources,
            env=env,
            daemon=DAEMON_FMT.format(jobdir),
            scene_list=out_fname,
            outdir=job_outdir,
            pkgdir=pkgdir,
            yamls_dir=yamls_dir,
            workers=workers,
        )

        if cleanup:
            pbs += CLEAN_UP_TEMPLATE.format(outdir=job_outdir)

        # write pbs script
        out_fname = pjoin(jobdir, FMT4.format(jobid=jobid))
        with open(out_fname, "w") as src:
            src.write(pbs)

        if test:
            click.echo(f"Mocking... Submitting Job: {jobid} ...Mocking")
            click.echo(f"qsub {out_fname}")
            continue

        os.chdir(dirname(out_fname))
        click.echo(f"Submitting Job: {jobid}")
        try:
            raw_output = subprocess.check_output(["qsub", out_fname])
        except subprocess.CalledProcessError as exc:
            logging.error("qsub failed with exit code %s", str(exc.returncode))
            logging.error(exc.output)
            raise

        if hasattr(raw_output, "decode"):
            matches = re.match(
                r"^(?P<nci_job_id>\d+\.gadi-pbs)$", raw_output.decode("utf-8")
            )
            if matches:
                nci_job_ids.append(matches.groupdict()["nci_job_id"])

    # return a list of the nci job ids
    return nci_job_ids


def _submit_summary(indir, outdir, batch_id, pbs_resources, env, job_ids, test):
    """Summarise the jobs submitted within the batchjob."""
    jobids = ":".join([j.split(".")[0] for j in job_ids])
    pbs = SUMMARY_TEMPLATE.format(
        pbs_resources=pbs_resources,
        env=env,
        indir=indir,
        outdir=outdir,
        jobids=jobids,
        batchid=batch_id,
    )

    out_fname = pjoin(indir, FMT5.format(batchid=batch_id))
    with open(out_fname, "w") as src:
        src.write(pbs)

    if test:
        click.echo(
            f"Mocking... Submitting Summary Job for batch: {batch_id} ...Mocking"
        )
        click.echo(f"qsub {out_fname}")
        return

    os.chdir(dirname(out_fname))
    click.echo(f"Submitting Summary Job for batch: {batch_id}")
    try:
        raw_output = subprocess.check_output(["qsub", out_fname])
    except subprocess.CalledProcessError as exc:
        logging.error("qsub failed with exit code %s", str(exc.returncode))
        logging.error(exc.output)
        raise

    if hasattr(raw_output, "decode"):
        matches = re.match(
            r"^(?P<nci_job_id>\d+\.gadi-pbs)$", raw_output.decode("utf-8")
        )
        if matches:
            job_id = matches.groupdict()["nci_job_id"]

    return job_id


def _submit_index(indir, outdir, batch_id, pbs_resources, env, job_id, test):
    """Submit a job that adds datasets to a datacube index."""
    if job_id:
        jobid = job_id.split(".")[0]
    else:
        jobid = ""
    pbs = INDEXING_TEMPLATE.format(
        pbs_resources=pbs_resources,
        env=env,
        indir=indir,
        outdir=outdir,
        jobid=jobid,
        batchid=batch_id,
    )

    out_fname = pjoin(indir, FMT6.format(batchid=batch_id))
    with open(out_fname, "w") as src:
        src.write(pbs)

    if test:
        click.echo(
            f"Mocking... Submitting Indexing Job for batch: {batch_id} ...Mocking"
        )
        return

    os.chdir(dirname(out_fname))
    click.echo(f"Submitting Indexing Job for batch: {batch_id}")
    try:
        raw_output = subprocess.check_output(["qsub", out_fname])
    except subprocess.CalledProcessError as exc:
        logging.error("qsub failed with exit code %s", str(exc.returncode))
        logging.error(exc.output)
        raise

    if hasattr(raw_output, "decode"):
        matches = re.match(
            r"^(?P<nci_job_id>\d+\.gadi-pbs)$", raw_output.decode("utf-8")
        )
        if matches:
            job_id = matches.groupdict()["nci_job_id"]

    return job_id


def _submit_archive(indir, outdir, archive_list, batch_id, pbs_resources, env, test):
    """Submit a job that archives datasets given a file listing UUIDs."""
    pbs = ARCHIVING_TEMPLATE.format(
        pbs_resources=pbs_resources,
        env=env,
        indir=indir,
        outdir=outdir,
        archive_list=archive_list,
    )

    out_fname = pjoin(indir, FMT8.format(batchid=batch_id))
    with open(out_fname, "w") as src:
        src.write(pbs)

    if test:
        click.echo(
            f"Mocking... Submitting Archiving Job for batch: {batch_id} ...Mocking"
        )
        return

    os.chdir(dirname(out_fname))
    click.echo(f"Submitting Archiving Job for batch: {batch_id}")
    try:
        raw_output = subprocess.check_output(["qsub", out_fname])
    except subprocess.CalledProcessError as exc:
        logging.error("qsub failed with exit code %s", str(exc.returncode))
        logging.error(exc.output)
        raise

    if hasattr(raw_output, "decode"):
        matches = re.match(
            r"^(?P<nci_job_id>\d+\.gadi-pbs)$", raw_output.decode("utf-8")
        )
        if matches:
            job_id = matches.groupdict()["nci_job_id"]

    return job_id


@click.command()
@click.option(
    "--level1-list",
    type=click.Path(exists=True, readable=True),
    help="The input level1 scene list.",
)
@click.option(
    "--workdir",
    type=click.Path(file_okay=False, writable=True),
    help="The base output working directory.",
)
@click.option(
    "--logdir",
    type=click.Path(file_okay=False, writable=True),
    help="The base logging and scripts output directory.",
)
@click.option(
    "--pkgdir",
    type=click.Path(file_okay=False, writable=True),
    help="The base output packaged directory.",
)
@click.option(
    "--yamls-dir",
    type=click.Path(file_okay=False),
    default="",
    help="The base directory for level-1 dataset documents.",
)
@click.option(
    "--env",
    type=click.Path(exists=True, readable=True),
    help="Environment script to source.",
)
@click.option(
    "--workers",
    type=click.IntRange(1, 48),
    default=30,
    help="The number of workers to request per node.",
)
@click.option("--nodes", default=0, help="The number of nodes to request.")
@click.option("--memory", default=192, help="The memory in GB to request per node.")
@click.option("--jobfs", default=50, help="The jobfs memory in GB to request per node.")
@click.option("--project", required=True, help="Project code to run under.")
@click.option(
    "--queue",
    default="normal",
    help="Queue to submit the job into, eg normal, express.",
)
@click.option(
    "--walltime", default="48:00:00", help="Job walltime in `hh:mm:ss` format."
)
@click.option("--email", default="", help="Notification email address.")
@click.option(
    "--index-datacube-env",
    type=click.Path(exists=True, readable=True),
    help="Datacube specific environment script to source.",
)
@click.option(
    "--archive-list",
    type=click.Path(exists=True, readable=True),
    help="UUID's of the scenes to archive.  This uses the environment specified in index-datacube-env.",
)
@click.option(
    "--cleanup",
    default=False,
    is_flag=True,
    help=("Clean-up work directory afterwards."),
)
@click.option(
    "--test",
    default=False,
    is_flag=True,
    help=("Test job execution (Don't submit the job to the " "PBS queue)."),
)
# pylint: disable=too-many-arguments
def main(
    level1_list,
    workdir,
    logdir,
    pkgdir,
    yamls_dir,
    env,
    workers,
    nodes,
    memory,
    jobfs,
    project,
    queue,
    walltime,
    email,
    index_datacube_env,
    archive_list,
    cleanup,
    test,
):
    """Equally partition a list of scenes across n nodes and submit
    n jobs into the PBS queue for ARD processing.
    """
    with open(level1_list) as src:
        scenes = src.readlines()
    if nodes == 0:
        nodes = _calc_nodes_req(len(scenes), walltime, workers)
    scattered = scatter(scenes, nodes)

    batchid = uuid.uuid4().hex[0:10]
    batch_logdir = pjoin(logdir, FMT1.format(batchid=batchid))
    batch_outdir = pjoin(workdir, FMT1.format(batchid=batchid))

    # Get a list of needed NCI projects, so that we can request access to their storage.
    fs_projects = _filesystem_projects(
        level1_list,
        # All other paths we expect the job to touch.
        env,
        logdir,
        workdir,
        pkgdir,
        yamls_dir,
    )
    fsys_projects = "+".join([FMT7.format(f_project=f) for f in fs_projects])

    # optionally set pbs email string
    pbs_resources = PBS_RESOURCES.format(
        project=project,
        queue=queue,
        walltime=walltime,
        memory=memory,
        ncpus=workers,
        jobfs=jobfs,
        filesystem_projects=fsys_projects,
        email=("#PBS -M " + email) if email else "",
    )

    if test:
        click.echo(f"Mocking... Submitting Batch: {batchid} ...Mocking")
    else:
        click.echo(f"Submitting Batch: {batchid}")

    click.echo(f"Executing Batch: {batchid}")
    nci_job_ids = _submit_multiple(
        scattered,
        env,
        batch_logdir,
        batch_outdir,
        pkgdir,
        yamls_dir,
        workers,
        pbs_resources,
        cleanup,
        test,
    )

    # job resources for batch summary
    pbs_resources = PBS_RESOURCES.format(
        project=project,
        queue="express",
        walltime="00:10:00",
        memory=6,
        ncpus=1,
        jobfs=2,
        filesystem_projects="".join(fsys_projects),
        email=("#PBS -M " + email) if email else "",
    )

    job_id = _submit_summary(
        batch_logdir, batch_logdir, batchid, pbs_resources, env, nci_job_ids, test
    )
    nci_job_ids.append(job_id)

    if index_datacube_env:
        pbs_resources = PBS_RESOURCES.format(
            project=project,
            queue="normal",
            walltime="00:30:00",
            memory=192,
            ncpus=48,
            jobfs=20,
            filesystem_projects="".join(fsys_projects),
            email=("#PBS -M " + email) if email else "",
        )
        index_job_id = _submit_index(
            batch_logdir,
            batch_logdir,
            batchid,
            pbs_resources,
            index_datacube_env,
            job_id,
            test,
        )
        nci_job_ids.append(index_job_id)

    if archive_list:
        if index_datacube_env:
            pbs_resources = PBS_RESOURCES.format(
                project=project,
                queue="normal",
                walltime="00:30:00",
                memory=192,
                ncpus=48,
                jobfs=20,
                filesystem_projects="".join(fsys_projects),
                email=("#PBS -M " + email) if email else "",
            )
            archive_job_id = _submit_archive(
                batch_logdir,
                batch_logdir,
                archive_list,
                batchid,
                pbs_resources,
                index_datacube_env,
                test,
            )
            nci_job_ids.append(archive_job_id)
        else:
            logging.error("Archive list given but --index-datacube-env not specified.")

    job_details = {"ardpbs_batch_id": batchid, "nci_job_ids": nci_job_ids}

    # Enable the job details to be picked up by the calling process
    click.echo(json.dumps(job_details))


if __name__ == "__main__":
    main()
