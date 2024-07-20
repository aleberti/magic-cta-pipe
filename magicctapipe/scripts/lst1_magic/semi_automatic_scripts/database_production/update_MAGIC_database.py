"""
The script updates the common MAGIC database from a given time range.
At the moment, to avoid accidentally destroying the previous database,
we save the updated database as a new file. If the path to the database is not found,
the script creates a new one. The start of the time interval
is the date of the beginning of the common MAGIC+LST1 observations.
The end of the time interval is the current date.

The MAGIC files that can be used for analysis are located in the IT cluster
in the following directory:
/fefs/onsite/common/MAGIC/data/M{tel_id}/event/Calibrated/{YYYY}/{MM}/{DD}

In this path, 'tel_id' refers to the telescope ID, which must be either 1 or 2.
'YYYY', 'MM', and 'DD' specify the date.
"""

import os
from datetime import datetime, timedelta

import pandas as pd


def fix_lists_and_convert(cell):
    """
    An additional function necessary to organize lists in the function table_magic_runs.
    The function remove brackets to avoid double lists and split on "][".

    Parameters
    -----------
    cell : str
        List of MAGIC runs from the date and the source.

    Returns
    -------
    list
        A list of unique integers representing the MAGIC runs.
    """

    parts = cell.replace("][", ",").strip("[]").split(",")
    return list(dict.fromkeys(int(item) for item in parts))

def table_magic_runs(df, date_min, date_max):

    """
    Generate a table with data filtered by the specified date range.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with general information about MAGIC+LST1 observations.
    date_min : str
        Start of the time interval (in LST convention).
    date_max : str
        End of the time interval (in LST convention).

    Returns
    -------
    pandas.DataFrame
        A DataFrame filtered by the specified date range.
    """
    
    df_selected_data = df.iloc[:, [2, 1, 25]]
    df_selected_data.columns = ["DATE", "source", "MAGIC_runs"]
    grouped_data = df_selected_data.groupby(["DATE", "source"])
    result_table = []

    for (date, source), group in grouped_data:
         if date >= date_min and date <= date_max: 
            runs_combined = group["MAGIC_runs"].sum()

            result_table.append(
                {"DATE": date, "source": source, "Run ID": runs_combined}
            )

    result = pd.DataFrame(result_table)
    result["Run ID"] = result["Run ID"].apply(fix_lists_and_convert)
    result_exploded = result.explode("Run ID")
    result_exploded_reset = result_exploded.reset_index(drop=True)
    return result_exploded_reset


def update_tables(database, DF, tel_id):
    """
    Updating the MAGIC database by comparison of data that are only in
    common MAGIC+LST1 database and not in the MAGIC database.
    Then, the function checks existing files and counts number of subruns.
    Data are added chronologically.

    The updated table DF may include new rows that contain NaN values in some cells.
    The function automatically filling NaN values withpredefined default values
    based on the column's data type.

    Parameters
    -----------
        database : pandas.DataFrame
            Table with informations about MAGIC runs from the date and the source from given time interval.
        DF : pandas.DataFrame
            The previous MAGIC database which we want to update.
        tel_id : int
            The telescope ID, which must be either 1 or 2.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with updated MAGIC database.
    """

    database["DATE"] = database["DATE"].astype(str)
    DF["DATE"] = DF["DATE"].astype(str)
    columns_to_compare = ["DATE", "source", "Run ID"]
    merged_df = pd.merge(
        database,
        DF[columns_to_compare],
        on=columns_to_compare,
        how="left",
        indicator=True,
    )
    non_matching_rows = merged_df[merged_df["_merge"] == "left_only"].drop(
        columns=["_merge"]
    )

    if non_matching_rows.empty:
        raise Exception("There is no un-updated data for a given time interval. ")
    else:

        non_matching_rows_reset = non_matching_rows.reset_index(drop=True)
        new_rows = []

        for index, row in non_matching_rows_reset.iterrows():
            date = row["DATE"]
            source = row["source"]
            run_id = row["Run ID"]
            run_id = str(run_id)

            date_obj = datetime.strptime(date, "%Y%m%d")
            date_obj += timedelta(days=1)
            new_date = datetime.strftime(date_obj, "%Y%m%d")
            YYYY = new_date[:4]
            MM = new_date[4:6]
            DD = new_date[6:8]
            Y = "_Y_"

            path = f"/fefs/onsite/common/MAGIC/data/M{tel_id}/event/Calibrated/{YYYY}/{MM}/{DD}"

            if os.path.exists(path):
                files = os.listdir(path)
                count_with_run_id = 0
                # Counter for files that include the run_id.
                for filename in files:
                    if Y in filename:
                        if new_date in filename:
                            if source in filename:
                                if run_id in filename:
                                    count_with_run_id += 1
                if count_with_run_id != 0:
                    new_rows.append(
                        {
                            "DATE": date,
                            "source": source,
                            "Run ID": run_id,
                            "number of subruns": count_with_run_id,
                        }
                    )

        new_rows = pd.DataFrame(new_rows)
        new_rows["DATE"] = pd.to_datetime(new_rows["DATE"])
        combined_df = pd.concat([DF, new_rows], ignore_index=True)
        combined_df["DATE"] = pd.to_datetime(combined_df["DATE"], errors="coerce")
        combined_df = combined_df.sort_values("DATE")

        combined_df["DATE"] = combined_df["DATE"].dt.strftime("%Y%m%d")
        combined_df["Run ID"] = combined_df["Run ID"].astype(int)
        combined_df.reset_index(drop=True, inplace=True)

        for column in combined_df.columns[4:]:
            not_null_data = combined_df[column].dropna()
            if not_null_data.empty:
                continue  # Skip if all values are NaN

            inferred_type = pd.api.types.infer_dtype(not_null_data, skipna=True)

            if inferred_type == "boolean":
                default_value = False
            elif inferred_type == "integer":
                default_value = 0
            elif inferred_type == "floating":
                default_value = 0.0
            elif inferred_type == "string":
                default_value = "NaN"
            else:
                continue

            combined_df[column] = (
                combined_df[column]
                .fillna(default_value)
                .astype(type(not_null_data.iloc[0]))
            )

        combined_df = combined_df.infer_objects()

    return combined_df

def create_new_database(df, date_min, date_max, tel_id):
    """
    Creating a new MAGIC database.

    Parameters
    -----------
    df : pandas.DataFrame
        Dataframe with general information about MAGIC+LST1 observations.
    date_min : str
        Start of the time interval (in LST convention).
    date_max : str
        End of the time interval (in LST convention).
    tel_id : int
        The telescope ID, which must be either 1 or 2.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with a new MAGIC database for all common MAGIC+LST1 observations.
    """

    database = table_magic_runs(df, date_min, date_max)
    new_rows = []

    for index, row in database.iterrows():
        date = row["DATE"]
        source = row["source"]
        run_id = row["Run ID"]
        run_id = str(run_id)

        date_obj = datetime.strptime(date, "%Y%m%d")
        date_obj += timedelta(days=1)
        new_date = datetime.strftime(date_obj, "%Y%m%d")
        YYYY = new_date[:4]
        MM = new_date[4:6]
        DD = new_date[6:8]
        Y = "_Y_"

        path = f"/fefs/onsite/common/MAGIC/data/M{tel_id}/event/Calibrated/{YYYY}/{MM}/{DD}"

        if os.path.exists(path):
            files = os.listdir(path)
            count_with_run_id = 0 
            # Counter for files that include the run_id.
            for filename in files:
                if Y in filename:
                    if new_date in filename:
                        if source in filename:
                            if run_id in filename:
                                count_with_run_id += 1
            if count_with_run_id != 0:
                new_rows.append(
                    {
                        "DATE": date,
                        "source": source,
                        "Run ID": run_id,
                        "number of subruns": count_with_run_id,
                    }
                )

    new_rows = pd.DataFrame(new_rows)

    return new_rows

def main():

    """Main function."""

    tel_id = [1, 2]

    df = pd.read_hdf(
        "/fefs/aswg/workspace/federico.dipierro/MAGIC_LST1_simultaneous_runs_info/simultaneous_obs_summary.h5",
        key="str/table",
    )

    # Set "" to generate a new database.
    previous_database_path = "/fefs/aswg/workspace/joanna.wojtowicz/data/Common_MAGIC_LST1_data_MAGIC_runs_subruns.h5"
    file_exists = os.path.exists(previous_database_path)

    if file_exists:

        # TO DO : set time interval - format YYYYMMDD
        date_min = "20240601"
        date_max = "20240718"

        print("Updating database...")

        database = table_magic_runs(df, date_min, date_max)

        for tel in tel_id:

            DF = pd.read_hdf(
                previous_database_path,
                key=f"MAGIC{tel}/runs_M{tel}",
            )

            if tel == 1:
                updated_df_1 = update_tables(database, DF, tel)
                print(updated_df_1)
            if tel == 2:
                updated_df_2 = update_tables(database, DF, tel)
                print(updated_df_2)
        # TO DO : set a path to save new database
        new_h5_file_path = (
            "/fefs/aswg/workspace/joanna.wojtowicz/output/update_database.h5"
        )

        try:
            updated_df_1.to_hdf(
                new_h5_file_path, key="MAGIC1/runs_M1", mode="w", format="table"
            )
            updated_df_2.to_hdf(
                new_h5_file_path, key="MAGIC2/runs_M2", mode="a", format="table"
            )
            print(f"File saved successfully at {new_h5_file_path}")

        except Exception as e:
            print(f"An error occurred: {e}")

    else:
        print("Database does not exist. Creating a new database...")

        date_min = "20191101"
        current_datetime = datetime.now()
        date_max = current_datetime.strftime("%Y%m%d")

        tel_id_M1 = 1
        tel_id_M2 = 2
        database_M1 = create_new_database(df, date_min, date_max, tel_id_M1)
        database_M2 = create_new_database(df, date_min, date_max, tel_id_M2)

        # TO DO : set a path to save a new database
        new_database_file_path = "/fefs/aswg/workspace/joanna.wojtowicz/output/Common_MAGIC_LST1_data_MAGIC_runs_subruns.h5"

        try:
            database_M1.to_hdf(
                new_database_file_path, key="MAGIC1/runs_M1", mode="w", format="table"
            )
            database_M2.to_hdf(
            	new_database_file_path, key="MAGIC2/runs_M2", mode="a", format="table"
            )
            print(f"File saved successfully at {new_database_file_path}")

        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
