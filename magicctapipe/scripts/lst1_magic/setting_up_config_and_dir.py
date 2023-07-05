"""
This script facilitates the usage of other two scripts
of the MCP, i.e. "lst1_magic_mc_dl0_to_dl1.py" and
"magic_calib_to_dl1.py". This script is more like a
"manager" that organizes the analysis process by:
1) Creating the necessary directories and subdirectories.
2) Generatign all the bash script files that convert the
MAGIC and MC files from DL0 to DL1.
3) Launching these jobs in the IT container.

Notice that in this stage we only use MAGIC + MC data.
No LST data is used here.

Standard usage:
$ python setting_up_config_and_dir.py

If you want to run only the MAGIC or only the MC conversion,
you can do as follows:

Only MAGIC:
$ python setting_up_config_and_dir.py --partial-analysis onlyMAGIC

Only MC:
$ python setting_up_config_and_dir.py --partial-analysis onlyMC

"""

import os
import numpy as np
import argparse
import glob
import time
import yaml
from pathlib import Path

def config_file_gen(ids, target_dir):
    
    """
    Here we create the configuration file needed for transforming DL0 into DL1
    """
    
    f = open(target_dir+'/config_DL0_to_DL1.yaml','w')
    #f.write("directories:\n    target: "+target_dir+"\n\n")    
    lines_of_config_file = [
    "mc_tel_ids:",
    "\n    LST-1: "+str(ids[0]),
    "\n    LST-2: "+str(ids[1]),
    "\n    LST-3: "+str(ids[2]),
    "\n    LST-4: "+str(ids[3]),
    "\n    MAGIC-I: "+str(ids[4]),
    "\n    MAGIC-II: "+str(ids[5]),
    "\n",
    "\nLST:",
    "\n    image_extractor:",
    '\n        type: "LocalPeakWindowSum"',
    "\n        window_shift: 4",
    "\n        window_width: 8",
    "\n",
    "\n    increase_nsb:",
    "\n        use: true",
    "\n        extra_noise_in_dim_pixels: 1.27",
    "\n        extra_bias_in_dim_pixels: 0.665",
    "\n        transition_charge: 8",
    "\n        extra_noise_in_bright_pixels: 2.08",
    "\n",
    "\n    increase_psf:",
    "\n        use: false",
    "\n        fraction: null",
    "\n",
    "\n    tailcuts_clean:",
    "\n        picture_thresh: 8",
    "\n        boundary_thresh: 4",
    "\n        keep_isolated_pixels: false",
    "\n        min_number_picture_neighbors: 2",
    "\n",
    "\n    time_delta_cleaning:",
    "\n        use: true",
    "\n        min_number_neighbors: 1",
    "\n        time_limit: 2",
    "\n",
    "\n    dynamic_cleaning:",
    "\n        use: true",
    "\n        threshold: 267",
    "\n        fraction: 0.03",
    "\n",
    "\n    use_only_main_island: false",
    "\n",
    "\nMAGIC:",
    "\n    image_extractor:",
    '\n        type: "SlidingWindowMaxSum"',
    "\n        window_width: 5",
    "\n        apply_integration_correction: false",
    "\n",
    "\n    charge_correction:",
    "\n        use: true",
    "\n        factor: 1.143",
    "\n",
    "\n    magic_clean:",
    "\n        use_time: true",
    "\n        use_sum: true",
    "\n        picture_thresh: 6",
    "\n        boundary_thresh: 3.5",
    "\n        max_time_off: 4.5",
    "\n        max_time_diff: 1.5",
    "\n        find_hotpixels: true",
    '\n        pedestal_type: "from_extractor_rndm"',
    "\n",
    "\n    muon_ring:",
    "\n        thr_low: 25",
    "\n        tailcut: [12, 8]",
    "\n        ring_completeness_threshold: 25",
    "\n"]
    
    f.writelines(lines_of_config_file)
    f.close()


def lists_and_bash_generator(particle_type, target_dir, MC_path, SimTel_version, telescope_ids, focal_length):

    """
    This function creates the lists list_nodes_gamma_complete.txt and list_folder_gamma.txt with the MC file paths.
    After that, it generates a few bash scripts to link the MC paths to each subdirectory. 
    These bash scripts will be called later in the main() function below. 
    """
    
    process_name = target_dir.split("/")[-2:][1]
    
    list_of_nodes = glob.glob(MC_path+"/node*")
    f = open(target_dir+f"/list_nodes_{particle_type}_complete.txt","w") # creating list_nodes_gammas_complete.txt
    for i in list_of_nodes:
        f.write(i+"/output_"+SimTel_version+"\n")   
    
    f.close()
    
    f = open(target_dir+f"/list_folder_{particle_type}.txt","w") # creating list_folder_gammas.txt
    for i in list_of_nodes:
        f.write(i.split("/")[-1]+"\n")   
    
    f.close()
    
    ####################################################################################
    ############ bash scripts that link the MC paths to each subdirectory. 
    ####################################################################################
    
    f = open(f"linking_MC_{particle_type}_paths.sh","w")
    lines_of_config_file = [
    "#!/bin/sh\n\n",
    "#SBATCH -p short\n",
    "#SBATCH -J "+process_name+"\n\n",
    "#SBATCH -N 1\n\n",
    "ulimit -l unlimited\n",
    "ulimit -s unlimited\n",
    "ulimit -a\n\n",
    "while read -r -u 3 lineA && read -r -u 4 lineB\n",
    "do\n",
    "    cd "+target_dir+f"/DL1/MC/{particle_type}\n",
    "    mkdir $lineB\n",
    "    cd $lineA\n",
    "    ls -lR *.gz |wc -l\n",
    "    ls *.gz > "+target_dir+f"/DL1/MC/{particle_type}/$lineB/list_dl0.txt\n",
    '    string=$lineA"/"\n',
    "    export file="+target_dir+f"/DL1/MC/{particle_type}/$lineB/list_dl0.txt\n\n",
    "    cat $file | while read line; do echo $string${line} >>"+target_dir+f"/DL1/MC/{particle_type}/$lineB/list_dl0_ok.txt; done\n\n",
    '    echo "folder $lineB  and node $lineA"\n',
    'done 3<"'+target_dir+f'/list_nodes_{particle_type}_complete.txt" 4<"'+target_dir+f'/list_folder_{particle_type}.txt"\n',
    ""]
    f.writelines(lines_of_config_file)
    f.close()
    
    
    ################################################################################################################
    ############################ bash script that applies lst1_magic_mc_dl0_to_dl1.py to all MC data files. 
    ################################################################################################################
    
    number_of_nodes = glob.glob(MC_path+"/node*")
    number_of_nodes = len(number_of_nodes) -1
    
    f = open(f"linking_MC_{particle_type}_paths_r.sh","w")
    lines_of_config_file = [
    '#!/bin/sh\n\n',
    '#SBATCH -p xxl\n',
    '#SBATCH -J '+process_name+'\n',
    '#SBATCH --array=0-'+str(number_of_nodes)+'%50\n',
    '#SBATCH --mem=10g\n',
    '#SBATCH -N 1\n\n',
    'ulimit -l unlimited\n',
    'ulimit -s unlimited\n',
    'ulimit -a\n',
    'cd '+target_dir+f'/DL1/MC/{particle_type}\n\n',
    'export INF='+target_dir+'\n',
    f'SAMPLE_LIST=($(<$INF/list_folder_{particle_type}.txt))\n',
    'SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n',
    'cd $SAMPLE\n\n',
    'export LOG='+target_dir+f'/DL1/MC/{particle_type}'+'/simtel_{$SAMPLE}_all.log\n',
    'cat list_dl0_ok.txt | while read line\n',
    'do\n',
    '    cd '+target_dir+'/../\n',
    '    conda run -n magic-lst python lst1_magic_mc_dl0_to_dl1.py --input-file $line --output-dir '+target_dir+f'/DL1/MC/{particle_type}/$SAMPLE --config-file '+target_dir+'/config_DL0_to_DL1.yaml >>$LOG 2>&1 --focal_length_choice '+focal_length+'\n\n',
    'done\n',
    ""]
    f.writelines(lines_of_config_file)
    f.close()
    
    
    
    
def lists_and_bash_gen_MAGIC(target_dir, telescope_ids, MAGIC_runs):

    """
    Below we create a bash script that links the the MAGIC data paths to each subdirectory. 
    """
    
    process_name = target_dir.split("/")[-2:][1]
    
    f = open("linking_MAGIC_data_paths.sh","w")
    f.write('#!/bin/sh\n\n')
    f.write('#SBATCH -p short\n')
    f.write('#SBATCH -J '+process_name+'\n')
    f.write('#SBATCH -N 1\n\n')
    f.write('ulimit -l unlimited\n')
    f.write('ulimit -s unlimited\n')
    f.write('ulimit -a\n')
    
    if telescope_ids[-1] > 0:
        for i in MAGIC_runs:
            f.write('export IN1=/fefs/onsite/common/MAGIC/data/M2/event/Calibrated/'+i[0].split("_")[0]+"/"+i[0].split("_")[1]+"/"+i[0].split("_")[2]+'\n')
            f.write('export OUT1='+target_dir+'/DL1/Observations/M2/'+i[0]+'/'+i[1]+'\n')
            f.write('ls $IN1/*'+i[1][-2:]+'.*_Y_*.root > $OUT1/list_dl0.txt\n')
    
    f.write('\n')
    if telescope_ids[-2] > 0:
        for i in MAGIC_runs:
            f.write('export IN1=/fefs/onsite/common/MAGIC/data/M1/event/Calibrated/'+i[0].split("_")[0]+"/"+i[0].split("_")[1]+"/"+i[0].split("_")[2]+'\n')
            f.write('export OUT1='+target_dir+'/DL1/Observations/M1/'+i[0]+'/'+i[1]+'\n')
            f.write('ls $IN1/*'+i[1][-2:]+'.*_Y_*.root > $OUT1/list_dl0.txt\n')
      
    f.close()
    
    if (telescope_ids[-2] > 0) or (telescope_ids[-1] > 0):
        for i in MAGIC_runs:
            if telescope_ids[-1] > 0:
            
                number_of_nodes = glob.glob('/fefs/onsite/common/MAGIC/data/M2/event/Calibrated/'+i[0].split("_")[0]+"/"+i[0].split("_")[1]+"/"+i[0].split("_")[2]+f'/*{i[1]}.*_Y_*.root')
                number_of_nodes = len(number_of_nodes) - 1 
                
                f = open(f"MAGIC-II_dl0_to_dl1_run_{i[1]}.sh","w")
                lines_of_config_file = [
                '#!/bin/sh\n\n',
                '#SBATCH -p long\n',
                '#SBATCH -J '+process_name+'\n',
                '#SBATCH --array=0-'+str(number_of_nodes)+'\n',     
                '#SBATCH -N 1\n\n',
                'ulimit -l unlimited\n',
                'ulimit -s unlimited\n',
                'ulimit -a\n\n',
                'export OUTPUTDIR='+target_dir+'/DL1/Observations/M2/'+i[0]+'/'+i[1]+'\n',
                'cd '+target_dir+'/../\n',
                'SAMPLE_LIST=($(<$OUTPUTDIR/list_dl0.txt))\n',
                'SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n\n',
                'export LOG=$OUTPUTDIR/real_0_1_task${SLURM_ARRAY_TASK_ID}.log\n',
                'conda run -n magic-lst python magic_calib_to_dl1.py --input-file $SAMPLE --output-dir $OUTPUTDIR --config-file '+target_dir+'/config_DL0_to_DL1.yaml >$LOG 2>&1\n',
                ""]
                f.writelines(lines_of_config_file)
                f.close()
                
            if telescope_ids[-2] > 0:
                
                number_of_nodes = glob.glob('/fefs/onsite/common/MAGIC/data/M1/event/Calibrated/'+i[0].split("_")[0]+"/"+i[0].split("_")[1]+"/"+i[0].split("_")[2]+f'/*{i[1]}.*_Y_*.root')
                number_of_nodes = len(number_of_nodes) - 1 
                
                f = open(f"MAGIC-I_dl0_to_dl1_run_{i[1]}.sh","w")
                lines_of_config_file = [
                '#!/bin/sh\n\n',
                '#SBATCH -p long\n',
                '#SBATCH -J '+process_name+'\n',
                '#SBATCH --array=0-'+str(number_of_nodes)+'\n',  
                '#SBATCH -N 1\n\n',
                'ulimit -l unlimited\n',
                'ulimit -s unlimited\n',
                'ulimit -a\n\n',
                'export OUTPUTDIR='+target_dir+'/DL1/Observations/M1/'+i[0]+'/'+i[1]+'\n',
                'cd '+target_dir+'/../\n',
                'SAMPLE_LIST=($(<$OUTPUTDIR/list_dl0.txt))\n',
                'SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}\n\n',
                'export LOG=$OUTPUTDIR/real_0_1_task${SLURM_ARRAY_TASK_ID}.log\n',
                'conda run -n magic-lst python magic_calib_to_dl1.py --input-file $SAMPLE --output-dir $OUTPUTDIR --config-file '+target_dir+'/config_DL0_to_DL1.yaml >$LOG 2>&1\n',
                ""]
                f.writelines(lines_of_config_file)
                f.close()
    
    
def directories_generator(target_dir, telescope_ids,MAGIC_runs):

    """
    Here we create all subdirectories for a given workspace and target name.
    """
    
    ###########################################
    ##################### MC
    ###########################################
        
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
        os.mkdir(target_dir+"/DL1")
        os.mkdir(target_dir+"/DL1/Observations")
        os.mkdir(target_dir+"/DL1/MC")
        os.mkdir(target_dir+"/DL1/MC/gammas")
        os.mkdir(target_dir+"/DL1/MC/gammadiffuse")
        os.mkdir(target_dir+"/DL1/MC/electrons")
        os.mkdir(target_dir+"/DL1/MC/protons")
        os.mkdir(target_dir+"/DL1/MC/helium")
    else:
        overwrite = input("MC directory for "+target_dir.split("/")[-1]+" already exists. Would you like to overwrite it? [only 'y' or 'n']: ")
        if overwrite == "y":
            os.system("rm -r "+target_dir)
            os.mkdir(target_dir)
            os.mkdir(target_dir+"/DL1")
            os.mkdir(target_dir+"/DL1/Observations")
            os.mkdir(target_dir+"/DL1/MC")
            os.mkdir(target_dir+"/DL1/MC/gammas")
            os.mkdir(target_dir+"/DL1/MC/gammadiffuse")
            os.mkdir(target_dir+"/DL1/MC/electrons")
            os.mkdir(target_dir+"/DL1/MC/protons")
            os.mkdir(target_dir+"/DL1/MC/helium")
        else:
            print("Directory not modified.")
    
    
    
    ###########################################
    ##################### MAGIC
    ###########################################
    
    if telescope_ids[-1] > 0:    
        if not os.path.exists(target_dir+"/DL1/Observations/M2"):
            os.mkdir(target_dir+"/DL1/Observations/M2")
            for i in MAGIC_runs:
                if not os.path.exists(target_dir+"/DL1/Observations/M2/"+i[0]):
                    os.mkdir(target_dir+"/DL1/Observations/M2/"+i[0])
                    os.mkdir(target_dir+"/DL1/Observations/M2/"+i[0]+"/"+i[1])
                else:
                    os.mkdir(target_dir+"/DL1/Observations/M2/"+i[0]+"/"+i[1])
    
    if telescope_ids[-2] > 0:
        if not os.path.exists(target_dir+"/DL1/Observations/M1"):
            os.mkdir(target_dir+"/DL1/Observations/M1")
            for i in MAGIC_runs:
                if not os.path.exists(target_dir+"/DL1/Observations/M1/"+i[0]):
                    os.mkdir(target_dir+"/DL1/Observations/M1/"+i[0])
                    os.mkdir(target_dir+"/DL1/Observations/M1/"+i[0]+"/"+i[1])
                else:
                    os.mkdir(target_dir+"/DL1/Observations/M1/"+i[0]+"/"+i[1])
    




def main():

    """ Here we read the config_general.yaml file and call the functions to generate the necessary directories, bash scripts and launching the jobs."""
    
    parser = argparse.ArgumentParser()
    
    #Here we are simply collecting the parameters from the command line, as input file, output directory, and configuration file
    parser.add_argument(
        "--partial-analysis",
        "-p",
        dest="partial_analysis",
        type=str,
        default="doEverything",
        help="You can type 'onlyMAGIC' or 'onlyMC' to run this script only on MAGIC or MC data, respectively.",
    )
    
    args = parser.parse_args()
    
    
    
    with open("config_general.yaml", "rb") as f:   # "rb" mode opens the file in binary format for reading
        config = yaml.safe_load(f)
    
    
    #Below we read the telescope IDs and runs
    telescope_ids = list(config["mc_tel_ids"].values())
    SimTel_version = config["general"]["SimTel_version"]
    MAGIC_runs_and_dates = config["general"]["MAGIC_runs"]
    MAGIC_runs = np.genfromtxt(MAGIC_runs_and_dates,dtype=str,delimiter=',') #READ LIST OF DATES AND RUNS: format table in a way that each line looks like "2020_11_19,5093174"
    focal_length = config["general"]["focal_length"]
    
    #Below we read the data paths
    target_dir = str(Path(config["directories"]["workspace_dir"]))+"/"+config["directories"]["target_name"]
    MC_gammas  = str(Path(config["directories"]["MC_gammas"]))
    MC_electrons = str(Path(config["directories"]["MC_electrons"]))
    MC_helium = str(Path(config["directories"]["MC_helium"]))
    MC_protons = str(Path(config["directories"]["MC_protons"]))
    MC_gammadiff = str(Path(config["directories"]["MC_gammadiff"]))
    
    
    print("***** Linking MC paths - this may take a few minutes ******")
    print("*** Reducing DL0 to DL1 data - this can take many hours ***")
    print("Process name: ",target_dir.split('/')[-2:][1])
    print("To check the jobs submitted to the cluster, type: squeue -n",target_dir.split('/')[-2:][1])
    
    directories_generator(target_dir, telescope_ids, MAGIC_runs) #Here we create all the necessary directories in the given workspace and collect the main directory of the target   
    config_file_gen(telescope_ids,target_dir)
    
    #Below we run the analysis on the MC data
    if not args.partial_analysis=='onlyMAGIC':       
        lists_and_bash_generator("gammas", target_dir, MC_gammas, SimTel_version, telescope_ids, focal_length) #gammas
        #lists_and_bash_generator("electrons", target_dir, MC_electrons, SimTel_version, telescope_ids, focal_length) #electrons
        #lists_and_bash_generator("helium", target_dir, MC_helium, SimTel_version, telescope_ids, focal_length) #helium
        lists_and_bash_generator("protons", target_dir, MC_protons, SimTel_version, telescope_ids, focal_length) #protons
        lists_and_bash_generator("gammadiffuse", target_dir, MC_gammadiff, SimTel_version, telescope_ids, focal_length) #gammadiffuse
        
        #Here we do the MC DL0 to DL1 conversion:
        list_of_MC = glob.glob("linking_MC_*s.sh")
        
        #os.system("RES=$(sbatch --parsable linking_MC_gammas_paths.sh) && sbatch --dependency=afterok:$RES MC_dl0_to_dl1.sh")
        
        for n,run in enumerate(list_of_MC):
            if n == 0:
                launch_jobs_MC =  f"linking{n}=$(sbatch --parsable {run}) && running{n}=$(sbatch --parsable --dependency=afterany:$linking{n} {run[0:-3]}_r.sh)"
            else:
                launch_jobs_MC = launch_jobs_MC + f" && linking{n}=$(sbatch --parsable --dependency=afterany:$running{n-1} {run}) && running{n}=$(sbatch --parsable --dependency=afterany:$linking{n} {run[0:-3]}_r.sh)"
        
        
        os.system(launch_jobs_MC)
    
    #Below we run the analysis on the MAGIC data
    if not args.partial_analysis=='onlyMC':
        lists_and_bash_gen_MAGIC(target_dir, telescope_ids, MAGIC_runs) #MAGIC real data
        if (telescope_ids[-2] > 0) or (telescope_ids[-1] > 0):
            
            list_of_MAGIC_runs = glob.glob("MAGIC-*.sh")
            
            for n,run in enumerate(list_of_MAGIC_runs):
                if n == 0:
                    launch_jobs =  f"linking=$(sbatch --parsable linking_MAGIC_data_paths.sh)  &&  RES{n}=$(sbatch --parsable --dependency=afterany:$linking {run})"
                else:
                    launch_jobs = launch_jobs + f" && RES{n}=$(sbatch --parsable --dependency=afterany:$RES{n-1} {run})"
            
            os.system(launch_jobs)
        
if __name__ == "__main__":
    main()

    

    
    
    
    
