"""
This script generates the bash scripts to merge the data 
files calling the script "merge_hdf_files.py" to 
merge the runs of M1 and M2 into M1-M2 runs.

Usage:
$ python merge_M1_M2_runs.py 
(-c config_file.yaml)

"""
import argparse
import os
import numpy as np
from magicctapipe import __version__
import glob
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def merge(scripts_dir, target_dir, source):
    """
    This function creates the bash scripts to run merge_hdf_files.py

    Parameters
    ----------
    scripts_dir: str
        Path to the scripts directory
    target_dir: str
        Path to the working directory
    """
    ST_list = [
        os.path.basename(x) for x in glob.glob(f"{target_dir}/v{__version__}/DL1/*")
    ]

    for p in ST_list:
        process_name = "merging_" + target_dir.split("/")[-2:][1]

        MAGIC_DL1_dir = target_dir + f"/v{__version__}" + "/DL1/" + p

        f = open(f"{source}_Merge_1_{p}.sh", "w")
        f.write("#!/bin/sh\n\n")
        f.write("#SBATCH -p short\n")
        f.write("#SBATCH -J " + process_name + "\n")
        f.write("#SBATCH -N 1\n\n")
        f.write("ulimit -l unlimited\n")
        f.write("ulimit -s unlimited\n")
        f.write("ulimit -a\n\n")

        if os.path.exists(MAGIC_DL1_dir + "/M1") & os.path.exists(
            MAGIC_DL1_dir + "/M2"
        ):
            dates = [os.path.basename(x) for x in glob.glob(f"{MAGIC_DL1_dir}/M1/*")]
            for i in dates:
                runs = [
                    os.path.basename(x) for x in glob.glob(f"{MAGIC_DL1_dir}/M2/{i}/*")
                ]
                for r in runs:
                    if (len(os.listdir(MAGIC_DL1_dir + f"/M1/{i}/{r}")) > 1) and (
                        len(os.listdir(MAGIC_DL1_dir + f"/M2/{i}/{r}"))
                    ) > 1:
                        if not os.path.exists(MAGIC_DL1_dir + f"/Merged/{i}/Merged"):
                            os.mkdir(f"{MAGIC_DL1_dir}/Merged/{i}/Merged")
                        if not os.path.exists(
                            MAGIC_DL1_dir + f"/Merged/{i}/Merged/logs"
                        ):
                            os.mkdir(f"{MAGIC_DL1_dir}/Merged/{i}/Merged/logs")
                        f.write(
                            f"time conda run -n magic-lst python {scripts_dir}/merge_hdf_files.py --input-dir {MAGIC_DL1_dir}/Merged/{i}/{r} --output-dir {MAGIC_DL1_dir}/Merged/{i}/Merged --run-wise >{MAGIC_DL1_dir}/Merged/{i}/Merged/logs/merge_{i}.log \n"
                        )

        f.close()


def main():
    """
    Here we read the config_general.yaml file, split the pronton sample into "test" and "train", and merge the MAGIC files.
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

    target_dir = str(
        Path(config["directories"]["workspace_dir"])
        / config["directories"]["target_name"]
    )
    source = config["directories"]["target_name"]
    scripts_dir = str(Path(config["directories"]["scripts_dir"]))

    print("***** Generating merge bashscripts...")
    merge(scripts_dir, target_dir, source)

    print("***** Running merge_hdf_files.py in the MAGIC data files...")
    print("Process name: merging_" + target_dir.split("/")[-2:][1])
    print(
        "To check the jobs submitted to the cluster, type: squeue -n merging_"
        + target_dir.split("/")[-2:][1]
    )

    # Below we run the bash scripts to merge the MAGIC files
    list_of_merging_scripts = np.sort(glob.glob(f"{source}_Merge_1_*.sh"))
    if len(list_of_merging_scripts) < 1:
        return
    for n, run in enumerate(list_of_merging_scripts):
        if n == 0:
            launch_jobs = f"merging{n}=$(sbatch --parsable {run})"
        else:
            launch_jobs = launch_jobs + f" && merging{n}=$(sbatch --parsable  {run})"

    # print(launch_jobs)
    os.system(launch_jobs)


if __name__ == "__main__":
    main()
