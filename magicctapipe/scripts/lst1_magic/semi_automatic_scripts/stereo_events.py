"""
This scripts generates and runs the bashscripts
to compute the stereo parameters of DL1 MC and
Coincident MAGIC+LST data files.

Usage:
$ python stereo_events.py (-c config.yaml)

If you want to compute the stereo parameters only the real data or only the MC data,
you can do as follows:

Only real data:
$ python stereo_events.py --analysis-type onlyReal (-c config.yaml)

Only MC:
$ python stereo_events.py --analysis-type onlyMC (-c config.yaml)
"""

import argparse
import glob
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import yaml

from magicctapipe import __version__

__all__ = ["configfile_stereo", "bash_stereo", "bash_stereoMC"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def configfile_stereo(ids, target_dir, source_name, NSB_match):

    """
    This function creates the configuration file needed for the event stereo step

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
    if not NSB_match:
        file_name = f"{target_dir}/{source_name}/config_stereo.yaml"
    else:
        file_name = f"{target_dir}/v{__version__}/{source_name}/config_stereo.yaml"
    with open(file_name, "w") as f:
        lines = [
            f"mc_tel_ids:\n    LST-1: {ids[0]}\n    LST-2: {ids[1]}\n    LST-3: {ids[2]}\n    LST-4: {ids[3]}\n    MAGIC-I: {ids[4]}\n    MAGIC-II: {ids[5]}\n\n",
            'stereo_reco:\n    quality_cuts: "(intensity > 50) & (width > 0)"\n    theta_uplim: "6 arcmin"\n',
        ]

        f.writelines(lines)


def bash_stereo(target_dir, source, env_name, NSB_match):

    """
    This function generates the bashscript for running the stereo analysis.

    Parameters
    ----------
    target_dir : str
        Path to the working directory
    source : str
        Target name
    env_name : str
        Name of the environment
    NSB_match : bool
        If real data are matched to pre-processed MCs or not
    """

    process_name = source
    if not NSB_match:
        if not os.path.exists(
            f"{target_dir}/{source}/DL1/Observations/Coincident_stereo"
        ):
            os.mkdir(f"{target_dir}/{source}/DL1/Observations/Coincident_stereo")

        listOfNightsLST = np.sort(
            glob.glob(f"{target_dir}/{source}/DL1/Observations/Coincident/*")
        )

        for nightLST in listOfNightsLST:
            stereoDir = f"{target_dir}/{source}/DL1/Observations/Coincident_stereo/{nightLST.split('/')[-1]}"
            if not os.path.exists(stereoDir):
                os.mkdir(stereoDir)

            os.system(
                f"ls {nightLST}/*LST*.h5 >  {nightLST}/list_coin.txt"
            )  # generating a list with the DL1 coincident data files.
            with open(f"{nightLST}/list_coin.txt", "r") as f:
                process_size = len(f.readlines()) - 1

            with open(f"StereoEvents_real_{nightLST.split('/')[-1]}.sh", "w") as f:
                lines = [
                    "#!/bin/sh\n\n",
                    "#SBATCH -p short\n",
                    f"#SBATCH -J {process_name}_stereo\n",
                    f"#SBATCH --array=0-{process_size}%100\n",
                    "#SBATCH -n 1\n\n",
                    f"#SBATCH --output={stereoDir}/logs/slurm-%x.%A_%a.out"
                    f"#SBATCH --error={stereoDir}/logs/slurm-%x.%A_%a.err"
                    "ulimit -l unlimited\n",
                    "ulimit -s unlimited\n",
                    "ulimit -a\n\n",
                    f"export INPUTDIR={nightLST}\n",
                    f"export OUTPUTDIR={stereoDir}\n",
                    "SAMPLE_LIST=($(<$INPUTDIR/list_coin.txt))\n",
                    "SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n",
                    "export LOG=$OUTPUTDIR/stereo_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log\n",
                    f"conda run -n {env_name} lst1_magic_stereo_reco --input-file $SAMPLE --output-dir $OUTPUTDIR --config-file {target_dir}/{source}/config_stereo.yaml >$LOG 2>&1",
                ]
                f.writelines(lines)
    else:
        if not os.path.exists(
            f"{target_dir}/v{__version__}/{source}/DL1CoincidentStereo"
        ):
            os.mkdir(f"{target_dir}/v{__version__}/{source}/DL1CoincidentStereo")

        listOfNightsLST = np.sort(
            glob.glob(f"{target_dir}/v{__version__}/{source}/DL1Coincident/*")
        )
        for nightLST in listOfNightsLST:
            stereoDir = f'{target_dir}/v{__version__}/{source}/DL1CoincidentStereo/{nightLST.split("/")[-1]}'
            if not os.path.exists(stereoDir):
                os.mkdir(stereoDir)
            if not os.path.exists(f"{stereoDir}/logs"):
                os.mkdir(f"{stereoDir}/logs")
            if not os.listdir(f"{nightLST}"):
                continue
            if len(os.listdir(nightLST)) < 2:
                continue
            os.system(
                f"ls {nightLST}/*LST*.h5 >  {stereoDir}/logs/list_coin.txt"
            )  # generating a list with the DL1 coincident data files.
            with open(f"{stereoDir}/logs/list_coin.txt", "r") as f:
                process_size = len(f.readlines()) - 1

            if process_size < 0:
                continue
            lines = [
                "#!/bin/sh\n\n",
                "#SBATCH -p short\n",
                f"#SBATCH -J {process_name}_stereo\n",
                f"#SBATCH --array=0-{process_size}\n",
                "#SBATCH -n 1\n\n",
                f"#SBATCH --output={stereoDir}/logs/slurm-%x.%A_%a.out"
                f"#SBATCH --error={stereoDir}/logs/slurm-%x.%A_%a.err"
                "ulimit -l unlimited\n",
                "ulimit -s unlimited\n",
                "ulimit -a\n\n",
                f"export INPUTDIR={nightLST}\n",
                f"export OUTPUTDIR={stereoDir}\n",
                "SAMPLE_LIST=($(<$OUTPUTDIR/logs/list_coin.txt))\n",
                "SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n",
                "export LOG=$OUTPUTDIR/logs/stereo_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log\n",
                f"conda run -n {env_name} lst1_magic_stereo_reco --input-file $SAMPLE --output-dir $OUTPUTDIR --config-file {target_dir}/v{__version__}/{source}/config_stereo.yaml >$LOG 2>&1",
            ]
            with open(f"{source}_StereoEvents_{nightLST.split('/')[-1]}.sh", "w") as f:
                f.writelines(lines)


def bash_stereoMC(target_dir, identification, env_name, source):

    """
    This function generates the bashscript for running the stereo analysis.

    Parameters
    ----------
    target_dir : str
        Path to the working directory
    identification : str
        Particle name. Options: protons, gammadiffuse, gammas, protons_test
    env_name : str
        Name of the environment
    source : str
        Name of the target source
    """

    process_name = source

    if not os.path.exists(
        f"{target_dir}/{source}/DL1/MC/{identification}/Merged/StereoMerged"
    ):
        os.mkdir(f"{target_dir}/{source}/DL1/MC/{identification}/Merged/StereoMerged")

    inputdir = f"{target_dir}/{source}/DL1/MC/{identification}/Merged"

    os.system(
        f"ls {inputdir}/dl1*.h5 >  {inputdir}/list_coin.txt"
    )  # generating a list with the DL1 coincident data files.
    with open(f"{inputdir}/list_coin.txt", "r") as f:
        process_size = len(f.readlines()) - 1

    with open(f"StereoEvents_MC_{identification}.sh", "w") as f:
        lines = [
            "#!/bin/sh\n\n",
            "#SBATCH -p xxl\n",
            f"#SBATCH -J {process_name}_stereo\n",
            f"#SBATCH --array=0-{process_size}%100\n",
            "#SBATCH --mem=8g\n",
            "#SBATCH -n 1\n\n",
            f"#SBATCH --output={inputdir}/StereoMerged/logs/slurm-%x.%A_%a.out"
            f"#SBATCH --error={inputdir}/StereoMerged/logs/slurm-%x.%A_%a.err"
            "ulimit -l unlimited\n",
            "ulimit -s unlimited\n",
            "ulimit -a\n\n",
            f"export INPUTDIR={inputdir}\n",
            f"export OUTPUTDIR={inputdir}/StereoMerged\n",
            "SAMPLE_LIST=($(<$INPUTDIR/list_coin.txt))\n",
            "SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n",
            "export LOG=$OUTPUTDIR/stereo_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log\n",
            f"conda run -n {env_name} lst1_magic_stereo_reco --input-file $SAMPLE --output-dir $OUTPUTDIR --config-file {target_dir}/{source}/config_stereo.yaml >$LOG 2>&1",
        ]
        f.writelines(lines)


def main():

    """
    Here we read the config_general.yaml file and call the functions defined above.
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

    parser.add_argument(
        "--analysis-type",
        "-t",
        choices=["onlyReal", "onlyMC"],
        dest="analysis_type",
        type=str,
        default="doEverything",
        help="You can type 'onlyReal' or 'onlyMC' to run this script only on real or MC data, respectively.",
    )

    args = parser.parse_args()
    with open(
        args.config_file, "rb"
    ) as f:  # "rb" mode opens the file in binary format for reading
        config = yaml.safe_load(f)

    target_dir = Path(config["directories"]["workspace_dir"])

    env_name = config["general"]["env_name"]

    NSB_match = config["general"]["NSB_matching"]
    telescope_ids = list(config["mc_tel_ids"].values())
    source = config["data_selection"]["source_name_output"]

    source_list = []
    if source is not None:
        source_list = joblib.load("list_sources.dat")

    else:
        source_list.append(source)
    for source_name in source_list:

        print("***** Generating file config_stereo.yaml...")
        configfile_stereo(telescope_ids, target_dir, source_name, NSB_match)

        # Below we run the analysis on the MC data
        if (
            (args.analysis_type == "onlyMC")
            or (args.analysis_type == "doEverything")
            and not NSB_match
        ):
            print("***** Generating the bashscript for MCs...")
            bash_stereoMC(target_dir, "gammadiffuse", env_name, source_name)
            bash_stereoMC(target_dir, "gammas", env_name, source_name)
            bash_stereoMC(target_dir, "protons", env_name, source_name)
            bash_stereoMC(target_dir, "protons_test", env_name, source_name)

            list_of_stereo_scripts = np.sort(glob.glob("StereoEvents_MC_*.sh"))

            for n, run in enumerate(list_of_stereo_scripts):
                if n == 0:
                    launch_jobs = f"stereo{n}=$(sbatch --parsable {run})"
                else:
                    launch_jobs = f"{launch_jobs} && stereo{n}=$(sbatch --parsable --dependency=afterany:$stereo{n-1} {run})"

            os.system(launch_jobs)

        # Below we run the analysis on the real data
        if not NSB_match:

            if (
                (args.analysis_type == "onlyReal")
                or (args.analysis_type == "doEverything")
                or NSB_match
            ):
                print("***** Generating the bashscript for real data...")
                bash_stereo(target_dir, source_name, env_name, NSB_match)

                list_of_stereo_scripts = np.sort(glob.glob("StereoEvents_real_*.sh"))
                print("***** Submitting processes to the cluster...")
                print(f"Process name: {source_name}_stereo")
                print(
                    f"To check the jobs submitted to the cluster, type: squeue -n {source_name}_stereo"
                )
                for n, run in enumerate(list_of_stereo_scripts):
                    if n == 0:
                        launch_jobs = f"stereo{n}=$(sbatch --parsable {run})"
                    else:
                        launch_jobs = f"{launch_jobs} && stereo{n}=$(sbatch --parsable --dependency=afterany:$stereo{n-1} {run})"

                os.system(launch_jobs)

        else:

            print("***** Generating the bashscript...")
            bash_stereo(target_dir, source_name, env_name, NSB_match)

            print("***** Submitting processess to the cluster...")
            print(f"Process name: {source_name}_stereo")
            print(
                f"To check the jobs submitted to the cluster, type: squeue -n {source_name}_stereo"
            )

            # Below we run the bash scripts to find the stereo events
            list_of_stereo_scripts = np.sort(
                glob.glob(f"{source_name}_StereoEvents*.sh")
            )
            if len(list_of_stereo_scripts) < 1:
                continue
            for n, run in enumerate(list_of_stereo_scripts):
                if n == 0:
                    launch_jobs = f"stereo{n}=$(sbatch --parsable {run})"
                else:
                    launch_jobs = (
                        f"{launch_jobs} && stereo{n}=$(sbatch --parsable {run})"
                    )

            os.system(launch_jobs)


if __name__ == "__main__":
    main()