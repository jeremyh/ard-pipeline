#!/usr/bin/env python

"""PBS submission scripts."""


import argparse
import os
import subprocess
import uuid
from os.path import dirname, exists
from os.path import join as pjoin

from wagl.tiling import scatter

PBS_RESOURCES = """#!/bin/bash
#PBS -P {project}
#PBS -q {queue}
#PBS -l walltime={hours}:00:00,mem={memory}GB,ncpus={ncpus},jobfs=50GB,other=pernodejobfs
#PBS -l wd
#PBS -me
#PBS -M {email}
"""

NODE_TEMPLATE = """{pbs_resources}
source {env}

{daemon}

luigi {options} --level1-list {scene_list} --outdir {outdir} --workers 16{scheduler}
"""

DSH_TEMPLATE = """{pbs_resources}
FILES=({files})

DAEMONS=({daemons})

OUTDIRS=({outdirs})

for i in "${{!FILES[@]}}"; do
  X=$(($i+1))
  pbsdsh -n $((16 *$X)) -- bash -l -c "source {env}; ${{DAEMONS[$i]}}; luigi \\
    {options} \\
    --level1-list ${{FILES[$i]}} \\
    --outdir ${{OUTDIRS[$i]}} \\
    --workers 16" &
done;
wait
"""


FMT1 = "level1-scenes-{jobid}.txt"
FMT2 = "wagl-{jobid}.bash"
DAEMON_FMT = "luigid --background --logdir {}"
ARD_FMT = "--module wagl.{workflow} ARD --model {model} --vertices '{vertices}' --method {method}{pq}"  # pylint: disable=line-too-long
TASK_FMT = "--module wagl.multifile_workflow CallTask --task {task}"


def _submit_dsh(
    scattered, options, env, batchid, batch_logdir, batch_outdir, pbs_resources, test
):
    """Submit a single PBSDSH formatted job."""
    files = []
    daemons = []
    outdirs = []
    jobids = []

    # setup each block of scenes for processing
    for block in scattered:
        jobid = uuid.uuid4().hex[0:6]
        jobids.append(jobid)
        jobdir = pjoin(batch_logdir, f"jobid-{jobid}")
        job_outdir = pjoin(batch_outdir, f"jobid-{jobid}")

        if not exists(jobdir):
            os.makedirs(jobdir)

        if not exists(job_outdir):
            os.makedirs(job_outdir)

        # write the block of scenes to process
        out_fname = pjoin(jobdir, FMT1.format(jobid=jobid))
        with open(out_fname, "w") as src:
            src.writelines(block)

        files.append(out_fname)
        daemons.append(DAEMON_FMT.format(jobdir))
        outdirs.append(job_outdir)

    files = [f'"{f}"\n' for f in files]
    daemons = [f'"{f}"\n' for f in daemons]
    outdirs = [f'"{f}"\n' for f in outdirs]

    pbs = DSH_TEMPLATE.format(
        pbs_resources=pbs_resources,
        env=env,
        options=options,
        files="".join(files),
        daemons="".join(daemons),
        outdirs="".join(outdirs),
    )

    out_fname = pjoin(batch_logdir, FMT2.format(jobid=batchid))
    with open(out_fname, "w") as src:
        src.write(pbs)

    print(f"Job ids:\n{jobids}")
    if test:
        print(f"qsub {out_fname}")
    else:
        os.chdir(dirname(out_fname))
        subprocess.call(["qsub", out_fname])


def _submit_multiple(
    scattered,
    options,
    env,
    batchid,
    batch_logdir,
    batch_outdir,
    local_scheduler,
    pbs_resources,
    test,
):
    """Submit multiple PBS formatted jobs."""
    print(f"Executing Batch: {batchid}")
    # setup and submit each block of scenes for processing
    for block in scattered:
        jobid = uuid.uuid4().hex[0:6]
        jobdir = pjoin(batch_logdir, f"jobid-{jobid}")
        job_outdir = pjoin(batch_outdir, f"jobid-{jobid}")

        if not exists(jobdir):
            os.makedirs(jobdir)

        if not exists(job_outdir):
            os.makedirs(job_outdir)

        # local or central scheduler
        if local_scheduler:
            daemon = ""
            scheduler = " --local-scheduler"
        else:
            daemon = DAEMON_FMT.format(jobdir)
            scheduler = ""

        out_fname = pjoin(jobdir, FMT1.format(jobid=jobid))
        with open(out_fname, "w") as src:
            src.writelines(block)

        pbs = NODE_TEMPLATE.format(
            pbs_resources=pbs_resources,
            env=env,
            daemon=daemon,
            options=options,
            scene_list=out_fname,
            outdir=job_outdir,
            scheduler=scheduler,
        )

        out_fname = pjoin(jobdir, FMT2.format(jobid=jobid))
        with open(out_fname, "w") as src:
            src.write(pbs)

        if test:
            print(f"Mocking... Submitting Job: {jobid} ...Mocking")
            print(f"qsub {out_fname}")
        else:
            os.chdir(dirname(out_fname))
            print(f"Submitting Job: {jobid}")
            subprocess.call(["qsub", out_fname])


# pylint: disable=too-many-arguments
def run(
    level1,
    vertices="(5, 5)",
    model="standard",
    method="linear",
    pixel_quality=False,
    outdir=None,
    logdir=None,
    env=None,
    nodes=10,
    project=None,
    queue="normal",
    hours=48,
    email="your.name@something.com",
    local_scheduler=False,
    dsh=False,
    test=False,
    singlefile=False,
    task=None,
):
    """Base level program."""
    with open(level1) as src:
        scenes = src.readlines()

    # scattered = scatter(filter_scenes(scenes), nodes)
    scattered = scatter(scenes, nodes)

    batchid = uuid.uuid4().hex[0:10]
    batch_logdir = pjoin(logdir, f"batchid-{batchid}")
    batch_outdir = pjoin(outdir, f"batchid-{batchid}")

    # compute resources
    memory = 32 * nodes if dsh else 32
    ncpus = 16 * nodes if dsh else 16

    pbs_resources = PBS_RESOURCES.format(
        project=project,
        queue=queue,
        hours=hours,
        memory=memory,
        ncpus=ncpus,
        email=email,
    )

    pq = " --pixel-quality" if pixel_quality else ""

    workflow = "singlefile_workflow" if singlefile else "multifile_workflow"

    # luigi task workflow options
    if task is None:
        options = ARD_FMT.format(
            workflow=workflow, model=model, pq=pq, vertices=vertices, method=method
        )
    else:
        options = TASK_FMT.format(task=task)

    if test:
        print(f"Mocking... Submitting Batch: {batchid} ...Mocking")
    else:
        print(f"Submitting Batch: {batchid}")

    if dsh:
        _submit_dsh(
            scattered,
            options,
            env,
            batchid,
            batch_logdir,
            batch_outdir,
            pbs_resources,
            test,
        )
    else:
        _submit_multiple(
            scattered,
            options,
            env,
            batchid,
            batch_logdir,
            batch_outdir,
            local_scheduler,
            pbs_resources,
            test,
        )


def _parser():
    """Argument parser."""
    description = (
        "Equally partition a list of scenes in n nodes and submit "
        "into the PBS queue. Optionally submit as multiple "
        "jobs into the PBS queue, or as a single job "
        "and executed using PBSDSH."
    )
    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(description=description, formatter_class=formatter)
    parser.add_argument(
        "--level1-list", help="The input level1 scene list.", required=True
    )
    parser.add_argument(
        "--vertices",
        default="(5, 5)",
        type=str,
        help=(
            "Number of vertices to evaluate the radiative "
            "transfer at. JSON styled string is required."
        ),
    )
    parser.add_argument(
        "--model",
        default="standard",
        help=("The type of ARD workflow to invoke, " "eg standard, nbar, sbt."),
    )
    parser.add_argument(
        "--method",
        default="shear",
        help=("The interpolation method to invoke, " "eg linear, shear, rbf."),
    )
    parser.add_argument(
        "--pixel-quality",
        action="store_true",
        help=("Whether to run the pixel quality workflow, " "if applicable, or not."),
    )
    parser.add_argument("--outdir", help="The base output directory.", required=True)
    parser.add_argument(
        "--logdir", required=True, help="The base logging and scripts output directory."
    )
    parser.add_argument("--env", help="Environment script to source.", required=True)
    parser.add_argument(
        "--nodes", type=int, help="The number of nodes to request.", default=10
    )
    parser.add_argument("--project", help="Project code to run under.", required=True)
    parser.add_argument(
        "--queue",
        default="normal",
        help=("Queue to submit the job into, " "eg normal, express."),
    )
    parser.add_argument("--hours", help="Job walltime in hours.", default=48)
    parser.add_argument(
        "--email", help="Notification email address.", default="your.name@something.com"
    )
    parser.add_argument(
        "--local-scheduler",
        action="store_true",
        help=("Use a local scheduler instead of a central " "scheduler."),
    )
    parser.add_argument(
        "--dsh", help="Run using PBS Distributed Shell.", action="store_true"
    )
    parser.add_argument(
        "--singlefile",
        action="store_true",
        help=(
            "Run wagl using the single-file workflow. "
            "Default is to output multiple files."
        ),
    )
    parser.add_argument(
        "--task",
        help=(
            "Specify a luigi Task contained within the "
            "wagl.multifile_workflow module and run "
            "each scene listed in level1-list through to "
            "that Task level."
        ),
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help=("Test job execution (Don't submit the job to " "the PBS queue)."),
    )
    return parser


def main():
    """Main execution."""
    parser = _parser()
    args = parser.parse_args()
    run(
        args.level1_list,
        args.vertices,
        args.model,
        args.method,
        args.pixel_quality,
        args.outdir,
        args.logdir,
        args.env,
        args.nodes,
        args.project,
        args.queue,
        args.hours,
        args.email,
        args.local_scheduler,
        args.dsh,
        args.test,
        args.singlefile,
        args.task,
    )


if __name__ == "__main__":
    main()
