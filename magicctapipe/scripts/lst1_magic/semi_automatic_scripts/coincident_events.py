"""
This scripts facilitates the usage of the script
"lst1_magic_event_coincidence.py". This script is
more like a "manager" that organizes the analysis
process by:
1) Creating the bash scripts for looking for
coincidence events between MAGIC and LST in each
night.
2) Creating the subdirectories for the coincident
event files.

Usage:
$ python coincident_events.py (-c config_file.yaml)
"""
import argparse
import glob
import logging
import os
from datetime import date as dtdt
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import yaml

from magicctapipe import __version__

__all__ = ["configfile_coincidence", "linking_bash_lst"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def configfile_coincidence(ids, target_dir, source_name, NSB_match):

    """
    This function creates the configuration file needed for the event coincidence step

    Parameters
    ----------
    ids : list
        List of telescope IDs
    target_dir : str
        Path to the working directory
    source_name : str
        Name of the target source
    NSB_match : bool
        If real data are matched to pre-processed MCs or not
    """

    lines = [
        f"mc_tel_ids:\n    LST-1: {ids[0]}\n    LST-2: {ids[1]}\n    LST-3: {ids[2]}\n    LST-4: {ids[3]}\n    MAGIC-I: {ids[4]}\n    MAGIC-II: {ids[5]}\n\n",
        'event_coincidence:\n    timestamp_type_lst: "dragon_time"  # select "dragon_time", "tib_time" or "ucts_time"\n    pre_offset_search: true\n    n_pre_offset_search_events: 100\n    window_half_width: "300 ns"\n',
        '    time_offset:\n        start: "-10 us"\n        stop: "0 us"\n',
    ]
    if not NSB_match:
        file_name = f"{target_dir}/{source_name}/config_coincidence.yaml"
    else:
        file_name = f"{target_dir}/v{__version__}/{source_name}/config_coincidence.yaml"

    with open(file_name, "w") as f:
        f.writelines(lines)


def linking_bash_lst(
    target_dir, LST_runs, source_name, LST_version, env_name, NSB_match
):

    """
    This function links the LST data paths to the working directory and creates bash scripts.

    Parameters
    ----------
    target_dir : str
        Path to the working directory
    LST_runs : matrix of strings
        This matrix ([['date','run'],['date','run']...]) is imported from *_LST_runs.txt files and tells the function where to find the LST data and link them to our working directory
    source_name : str
        Target name
    LST_version : str
        The lstchain version used to process the LST data
    env_name : str
        Name of the conda environment
    NSB_match : bool
        If real data are matched to pre-processed MCs or not
    """

    if (len(LST_runs) == 2) and (len(LST_runs[0]) == 10):
        LST = LST_runs

        LST_runs = []
        LST_runs.append(LST)

    if (len(LST_runs) == 2) and (len(LST_runs[0]) == 10):
        dt = LST_runs
        LST_runs = []
        LST_runs.append(dt)
    if NSB_match:
        coincidence_DL1_dir = f"{target_dir}/v{__version__}/{source_name}"
        if not os.path.exists(f"{coincidence_DL1_dir}/DL1Coincident/"):
            os.mkdir(f"{coincidence_DL1_dir}/DL1Coincident")

        MAGIC_DL1_dir = f"{target_dir}/v{__version__}/{source_name}/DL1"

        dates = [
            os.path.basename(x) for x in glob.glob(f"{MAGIC_DL1_dir}/Merged/Merged_*")
        ]

        for d in dates:
            Y_M = int(d.split("_")[1])
            M_M = int(d.split("_")[2])
            D_M = int(d.split("_")[3])

            day_MAGIC = dtdt(Y_M, M_M, D_M)

            delta = timedelta(days=1)
            for i in LST_runs:
                Y_L = i[0].split("_")[0]
                M_L = i[0].split("_")[1]
                D_L = i[0].split("_")[2]
                day_LST = dtdt(int(Y_L), int(M_L), int(D_L))
                if day_MAGIC == day_LST + delta:

                    lstObsDir = (
                        i[0].split("_")[0] + i[0].split("_")[1] + i[0].split("_")[2]
                    )

                    inputdir = (
                        f"/fefs/aswg/data/real/DL1/{lstObsDir}/{LST_version}/tailcut84"
                    )
                    if not os.path.exists(
                        f"{coincidence_DL1_dir}/DL1Coincident/{lstObsDir}"
                    ):
                        os.mkdir(f"{coincidence_DL1_dir}/DL1Coincident/{lstObsDir}")
                    if not os.path.exists(
                        f"{coincidence_DL1_dir}/DL1Coincident/{lstObsDir}/logs"
                    ):
                        os.mkdir(
                            f"{coincidence_DL1_dir}/DL1Coincident/{lstObsDir}/logs"
                        )

                    outputdir = f"{coincidence_DL1_dir}/DL1Coincident/{lstObsDir}"
                    list_of_subruns = np.sort(
                        glob.glob(f"{inputdir}/dl1*Run*{i[1]}*.*.h5")
                    )
                    if os.path.exists(f"{outputdir}/logs/list_LST"):
                        with open(f"{outputdir}/logs/list_LST", "a") as LSTdataPathFile:
                            for subrun in list_of_subruns:
                                LSTdataPathFile.write(
                                    f"{subrun}\n"
                                )  # If this files already exists, simply append the new information
                    else:
                        with open(
                            f"{outputdir}/logs/list_LST.txt", "w"
                        ) as f:  # If the file list_LST.txt does not exist, it will be created here
                            for subrun in list_of_subruns:
                                f.write(f"{subrun}\n")

                    if not os.path.exists(f"{outputdir}/logs/list_LST.txt"):
                        continue
                    with open(f"{outputdir}/logs/list_LST.txt", "r") as f:
                        process_size = len(f.readlines()) - 1

                    if process_size < 0:
                        continue
                    lines = [
                        "#!/bin/sh\n\n",
                        "#SBATCH -p short\n",
                        f"#SBATCH -J {source_name}_coincidence\n",
                        f"#SBATCH --array=0-{process_size}\n",
                        "#SBATCH --mem=8g\n",
                        "#SBATCH -n 1\n\n",
                        f"#SBATCH --output={outputdir}/logs/slurm-%x.%j.out"
                        f"#SBATCH --error={outputdir}/logs/slurm-%x.%j.err"
                        "ulimit -l unlimited\n",
                        "ulimit -s unlimited\n",
                        "ulimit -a\n\n",
                        f"export INM={MAGIC_DL1_dir}/Merged/Merged_{str(Y_M).zfill(4)}_{str(M_M).zfill(2)}_{str(D_M).zfill(2)}\n",
                        f"export OUTPUTDIR={outputdir}\n",
                        "SAMPLE_LIST=($(<$OUTPUTDIR/logs/list_LST.txt))\n",
                        "SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n",
                        "export LOG=$OUTPUTDIR/logs/coincidence_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log\n",
                        f"conda run -n {env_name} lst1_magic_event_coincidence --input-file-lst $SAMPLE --input-dir-magic $INM --output-dir $OUTPUTDIR --config-file {target_dir}/v{__version__}/{source_name}/config_coincidence.yaml >$LOG 2>&1",
                    ]
                    with open(
                        f"{source_name}_LST_coincident_{outputdir.split('/')[-1]}.sh",
                        "w",
                    ) as f:
                        f.writelines(lines)
    else:
        coincidence_DL1_dir = f"{target_dir}/{source_name}/DL1/Observations"
        if not os.path.exists(f"{coincidence_DL1_dir}/Coincident"):
            os.mkdir(f"{coincidence_DL1_dir}/Coincident")

        for i in LST_runs:
            lstObsDir = i[0].split("_")[0] + i[0].split("_")[1] + i[0].split("_")[2]
            inputdir = f"/fefs/aswg/data/real/DL1/{lstObsDir}/{LST_version}/tailcut84"
            outputdir = f"{coincidence_DL1_dir}/Coincident/{lstObsDir}"
            list_of_subruns = np.sort(glob.glob(f"{inputdir}/dl1*Run*{i[1]}*.*.h5"))
            if os.path.exists(f"{outputdir}/list_LST.txt"):
                with open(f"{outputdir}/list_LST.txt", "a") as LSTdataPathFile:
                    for subrun in list_of_subruns:
                        LSTdataPathFile.write(
                            f"{subrun}\n"
                        )  # If this files already exists, simply append the new information
            else:
                os.mkdir(outputdir)
                with open(
                    f"{outputdir}/list_LST.txt", "w"
                ) as f:  # If the file list_LST.txt does not exist, it will be created here
                    for subrun in list_of_subruns:
                        f.write(f"{subrun}\n")
        process_name = source_name

        listOfNightsLST = np.sort(
            glob.glob(f"{target_dir}/{source_name}/DL1/Observations/Coincident/*")
        )
        listOfNightsMAGIC = np.sort(
            glob.glob(f"{target_dir}/{source_name}/DL1/Observations/Merged/Merged*")
        )

        for nightMAGIC, nightLST in zip(listOfNightsMAGIC, listOfNightsLST):
            with open(f"{nightLST}/list_LST.txt", "r") as f:
                process_size = len(f.readlines()) - 1

            with open(f"LST_coincident_{nightLST.split('/')[-1]}.sh", "w") as f:
                lines = [
                    "#!/bin/sh\n\n",
                    "#SBATCH -p short\n",
                    f"#SBATCH -J {process_name}_coincidence\n",
                    f"#SBATCH --array=0-{process_size}%50\n",
                    "#SBATCH --mem=8g\n",
                    "#SBATCH -n 1\n\n",
                    f"#SBATCH --output={nightLST}/slurm-%x.%j.out"
                    f"#SBATCH --error={nightLST}/slurm-%x.%j.err"
                    "ulimit -l unlimited\n",
                    "ulimit -s unlimited\n",
                    "ulimit -a\n\n",
                    f"export INM={nightMAGIC}\n",
                    f"export OUTPUTDIR={nightLST}\n",
                    "SAMPLE_LIST=($(<$OUTPUTDIR/list_LST.txt))\n",
                    "SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n",
                    "export LOG=$OUTPUTDIR/coincidence_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log\n",
                    f"conda run -n {env_name} lst1_magic_event_coincidence --input-file-lst $SAMPLE --input-dir-magic $INM --output-dir $OUTPUTDIR --config-file {target_dir}/{source_name}/config_coincidence.yaml >$LOG 2>&1",
                ]
                f.writelines(lines)


def main():

    """
    Here we read the config file and call the functions defined above.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-file",
        "-c",
        dest="config_file",
        type=str,
        default="./config_general.yaml",
        help="Path to a configuration file",
    )

    args = parser.parse_args()
    with open(
        args.config_file, "rb"
    ) as f:  # "rb" mode opens the file in binary format for reading
        config = yaml.safe_load(f)

    telescope_ids = list(config["mc_tel_ids"].values())
    target_dir = Path(config["directories"]["workspace_dir"])

    NSB_match = config["general"]["NSB_matching"]
    env_name = config["general"]["env_name"]
    LST_version = config["general"]["LST_version"]

    source = config["data_selection"]["source_name_output"]

    source_list = []
    if source is not None:
        source_list = joblib.load("list_sources.dat")

    else:
        source_list.append(source)
    for source_name in source_list:

        print("***** Generating file config_coincidence.yaml...")
        configfile_coincidence(telescope_ids, target_dir, source_name, NSB_match)

        LST_runs_and_dates = f"{source_name}_LST_runs.txt"
        LST_runs = np.genfromtxt(LST_runs_and_dates, dtype=str, delimiter=",")

        if not NSB_match:
            print("***** Linking the paths to LST data files...")

            print("***** Generating the bashscript...")
            linking_bash_lst(
                target_dir, LST_runs, source_name, LST_version, env_name, NSB_match
            )  # linking the data paths to the current working directory

            print("***** Submitting processess to the cluster...")
            print(f"Process name: {source_name}_coincidence")
            print(
                f"To check the jobs submitted to the cluster, type: squeue -n {source_name}_coincidence"
            )

            # Below we run the bash scripts to find the coincident events
            list_of_coincidence_scripts = np.sort(glob.glob("LST_coincident*.sh"))

            for n, run in enumerate(list_of_coincidence_scripts):
                if n == 0:
                    launch_jobs = f"coincidence{n}=$(sbatch --parsable {run})"
                else:
                    launch_jobs = (
                        f"{launch_jobs} && coincidence{n}=$(sbatch --parsable {run})"
                    )

            os.system(launch_jobs)
        else:

            try:

                print("***** Linking the paths to LST data files...")

                print("***** Generating the bashscript...")
                linking_bash_lst(
                    target_dir,
                    LST_runs,
                    source_name,
                    LST_version,
                    env_name,
                    NSB_match,
                )  # linking the data paths to current working directory

                print("***** Submitting processess to the cluster...")
                print(f"Process name: {source_name}_coincidence")
                print(
                    f"To check the jobs submitted to the cluster, type: squeue -n {source_name}_coincidence"
                )

                # Below we run the bash scripts to find the coincident events
                list_of_coincidence_scripts = np.sort(
                    glob.glob(f"{source_name}_LST_coincident*.sh")
                )
                if len(list_of_coincidence_scripts) < 1:
                    continue
                for n, run in enumerate(list_of_coincidence_scripts):
                    if n == 0:
                        launch_jobs = f"coincidence{n}=$(sbatch --parsable {run})"
                    else:
                        launch_jobs = f"{launch_jobs} && coincidence{n}=$(sbatch --parsable {run})"

                os.system(launch_jobs)

            except OSError as exc:
                print(exc)


if __name__ == "__main__":
    main()
