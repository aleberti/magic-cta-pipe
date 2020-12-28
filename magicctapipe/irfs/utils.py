import astropy.units as u
from astropy.table import QTable
from astropy import table

from pyirf.simulations import SimulatedEventsInfo

from magicctapipe.utils.filedir import *


def read_simu_info_mcp_sum_num_showers(file_list):
    """Function to read simulation information from DL2 files and sum the simultated
    showers. Assumes that all the mc_headers are equal

    Parameters
    ----------
    file_list : list
        magic-cta-pipe DL2 file list

    Returns
    -------
    pd.DataFrame
        mc_header with sum num showers
    """
    d = read_mc_header(file_list[0])
    num_showers = 0
    for i, file in enumerate(file_list):
        num_showers += int(read_mc_header(file)["num_showers"])
    d["num_showers"] = num_showers
    return d


def convert_simu_info_mcp_to_pyirf(file_list):
    """Function to convert simulation information from magic-cta-pipe DL2 files to 
    pyirf format

    Parameters
    ----------
    file_list : file list
        magic-cta-pipe DL2 file list

    Returns
    -------
    SimulatedEventsInfo
        pyirf_simu_info
    """
    simu_info = read_simu_info_mcp_sum_num_showers(file_list)
    pyirf_simu_info = SimulatedEventsInfo(
        n_showers=int(simu_info.num_showers) * int(simu_info.shower_reuse),
        energy_min=float(simu_info.energy_range_min) * u.TeV,
        energy_max=float(simu_info.energy_range_max) * u.TeV,
        max_impact=float(simu_info.max_scatter_range) * u.m,
        spectral_index=float(simu_info.spectral_index),
        viewcone=float(simu_info.max_viewcone_radius) * u.deg,
    )
    return pyirf_simu_info


def read_dl2_mcp_to_pyirf_MAGIC_LST_list(
    file_mask, reco_key="dl2/reco", useless_cols=[], max_files=0
):
    """Function to

    Parameters
    ----------
    file_mask : str
        file mask for magic-cta-pipe DL2 files
    reco_key : str, optional
        key for DL2 reco files, by default "dl2/reco"
    useless_cols : list, optional
        columns not used, by default []
    max_files : int, optional
        max number of files to be processed, 0 to process all of them, by default 0

    Returns
    -------
    tuple
        events, pyirf_simu_info
    """
    name_mapping = {
        "tel_alt": "pointing_alt",
        "tel_az": "pointing_az",
        "energy_reco": "reco_energy",
        "alt_reco": "reco_alt",
        "az_reco": "reco_az",
        "intensity_width_1": "leakage_intensity_width_1",
        "intensity_width_2": "leakage_intensity_width_2",
        "event_class_0": "gh_score",
        "pos_angle_shift_reco": "reco_source_fov_offset",  # ???
    }

    unit_mapping = {
        "true_energy": u.TeV,
        "reco_energy": u.TeV,
        "pointing_alt": u.rad,
        "pointing_az": u.rad,
        "true_alt": u.rad,
        "true_az": u.rad,
        "reco_alt": u.rad,
        "reco_az": u.rad,
    }
    file_list = glob.glob(file_mask)

    if max_files > 0:
        file_list = file_list[:max_files]

    pyirf_simu_info = convert_simu_info_mcp_to_pyirf(file_list)

    first_time = False
    for i, file in enumerate(file_list):
        try:
            events_ = pd.read_hdf(file, key=reco_key).rename(columns=name_mapping)
            if useless_cols != []:
                events_ = events_.drop(useless_cols, axis=1, errors="ignore")
            if not first_time:
                events = events_
                first_time = True
            else:
                events = events.append(events_)
        except Exception as e:
            print(f"ERROR: skipping file {file}\n{e}")

    events = table.QTable.from_pandas(events)
    for k, v in unit_mapping.items():
        events[k] *= v

    return events, pyirf_simu_info
