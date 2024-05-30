"""
Script to fill the 'nsb' column of the LST database. To be called after nsb_level.py

Usage: python nsb_to_h5.py
"""

import glob
import logging

import numpy as np
import pandas as pd

__all__ = ["collect_nsb"]

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


def collect_nsb(df_LST):
    """
    Here we collect NSB values from .txt files and store them into the dataframe

    Parameters
    ----------
    df_LST : :class:`pandas.DataFrame`
        Dataframe collecting the LST1 runs (produced by the create_LST_table script)

    Returns
    -------
    :class:`pandas.DataFrame`
        Same dataframe as the input one, but with NSB values added in the 'nsb' column (for the runs processed by nsb_level.py)
    """
    nsb_files = glob.glob("nsb_LST_*.txt")
    df_LST = df_LST.set_index("LST1_run")
    for file_nsb in nsb_files:
        run = file_nsb.split("_")[3]
        run = run.split(".")[0]
        nsb = np.nan
        with open(file_nsb) as ff:
            line_str = ff.readline().rstrip("\n")
            nsb = line_str.split(",")[2]

        df_LST.loc[run, "nsb"] = float(nsb)
    df_LST = df_LST.reset_index()
    return df_LST


def main():

    """
    Main function
    """

    df_LST = pd.read_hdf(
        "/fefs/aswg/workspace/elisa.visentin/auto_MCP_PR/observations_LST.h5",
        key="joint_obs",
    )

    df_new = collect_nsb(df_LST)

    df_new = df_new.sort_values(by=["DATE", "source", "LST1_run"])

    df_new.loc[df_new["error_code_nsb"].isna(), "error_code_nsb"] = "1"

    df_new.loc[df_new["nsb"].notna(), "error_code_nsb"] = "0"
    df_new.loc[df_new["nsb"] > 3.0, "error_code_nsb"] = "2"

    df_new = df_new[
        [
            "source",
            "DATE",
            "LST1_run",
            "MAGIC_stereo",
            "MAGIC_trigger",
            "MAGIC_HV",
            "nsb",
            "lstchain_versions",
            "last_lstchain_file",
            "processed_lstchain_file",
            "error_code_nsb",
            "error_code_coincidence",
            "error_code_stereo",
        ]
    ]
    df_new.to_hdf(
        "/fefs/aswg/workspace/elisa.visentin/auto_MCP_PR/observations_LST.h5",
        key="joint_obs",
        mode="w",
    )


if __name__ == "__main__":
    main()