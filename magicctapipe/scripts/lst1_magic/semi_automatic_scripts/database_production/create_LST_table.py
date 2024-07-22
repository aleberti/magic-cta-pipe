"""
Create a new h5 table from the one of joint observations.

Only the columns needed to produce the lists of LST runs to be processed are preserved, and two columns are added to store NSB level and error codes
"""

import argparse
import os

import numpy as np
import pandas as pd
import yaml

from magicctapipe.io import resource_file


def main():

    """
    Main function
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--begin-date",
        "-b",
        dest="begin",
        type=int,
        default=0,
        help="First date to update database (YYYYMMDD)",
    )
    parser.add_argument(
        "--end-date",
        "-e",
        dest="end",
        type=int,
        default=0,
        help="End date to update database (YYYYMMDD)",
    )

    args = parser.parse_args()
    config_file = resource_file("database_config.yaml")

    with open(
        config_file, "rb"
    ) as fc:  # "rb" mode opens the file in binary format for reading
        config_dict = yaml.safe_load(fc)

    out_h5 = config_dict["database_paths"]["LST"]
    out_key = config_dict["database_keys"]["LST"]

    df = pd.read_hdf(
        config_dict["database_paths"]["input_1"],
        key=config_dict["database_keys"]["input_1"],
    )  # TODO: put this file in a shared folder
    df2 = pd.read_hdf(
        config_dict["database_paths"]["input_2"],
        key=config_dict["database_keys"]["input_2"],
    )  # TODO: put this file in a shared folder
    df = pd.concat([df, df2]).drop_duplicates(subset="LST1_run", keep="first")
    if args.begin != 0:
        df = df[df["DATE"] >= args.begin]
    if args.end != 0:
        df = df[df["DATE"] <= args.end]

    needed_cols = [
        "source",
        "DATE",
        "LST1_run",
        "MAGIC_stereo",
        "MAGIC_trigger",
        "MAGIC_HV",
    ]
    df_cut = df[needed_cols]

    df_cut = df_cut.assign(nsb=np.nan)
    df_cut = df_cut.assign(lstchain_versions="[]")
    df_cut = df_cut.assign(last_lstchain_file="")
    df_cut = df_cut.assign(processed_lstchain_file="")
    df_cut = df_cut.assign(error_code_nsb=-1)

    #df_cut = df_cut.assign(error_code_coincidence=-1)
    #df_cut = df_cut.assign(error_code_stereo=-1)

    if os.path.isfile(out_h5):
        df_old = pd.read_hdf(
            out_h5,
            key=out_key,
        )
        df_cut = pd.concat([df_old, df_cut]).drop_duplicates(
            subset="LST1_run", keep="first"
        )
        df_cut = df_cut.sort_values(by=["DATE", "source"])
        # TODO check if fine with update and nsb
    df_cut = df_cut.reset_index(drop=True)
    df_cut.to_hdf(
        out_h5,
        key=out_key,
        mode="w",
        min_itemsize={
            "lstchain_versions": 20,
            "last_lstchain_file": 90,
            "processed_lstchain_file": 90,
        },
    )


if __name__ == "__main__":
    main()
