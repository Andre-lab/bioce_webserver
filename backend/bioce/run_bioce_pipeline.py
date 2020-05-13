"""
Pipeline for running BIOCE from raw pdb file and saxs data
"""
from backend.bioce.preparePepsi import (
    generate_file_list,
    generate_weights,
    process_pdbs_with_experimental,
)
import backend.bioce.variationalBayesian as vbi
import backend.bioce.fullBayesian as cbi
import zipfile
import numpy as np
import os
import pickle


def read_file_safe(filename, dtype="float64", skip_lines=0):
    """
    Simple check if file exists
    :param filename:
    :return:
    """
    try:
        results = np.genfromtxt(filename, dtype=dtype, skip_footer=skip_lines)
    except IOError as err:
        print(os.strerror(err.errno))
    return results

def savetext(filename, string_array):
    """

    :param string_array:
    :return:
    """
    output_file = open(filename,'w')
    for name in string_array:
        output_file.write(name+" ")
    output_file.close()

def simulate_profiles(directory, pdb_list, experimental_filename):
    """

    :param pdb_list_name:
    :param experimental_filename:
    :return:
    """
    generate_file_list(directory, pdb_list)
    generate_weights(directory, pdb_list)
    intensities = process_pdbs_with_experimental(directory, pdb_list, experimental_filename)
    simulate_profiles = os.path.join(directory, "SimulatedIntensities.txt")
    np.savetxt(simulate_profiles, intensities)


def run_variational(simulated, priors, experimental, output, file_list, weight_cut):
    """

    :param simulated:
    :param priors:
    :param experimental:
    :param output:
    :param file_list:
    :param weight_cut:
    :return:
    """

    (number_of_measures, number_of_structures) = vbi.extract_parameters(simulated)

    #Setting up values for default simplified run
    number_of_cs_measures = 1
    ncurves = 1
    restart = 0
    structure_energies = 'None'
    nprocs = 4
    skip_vbw = 0
    cs_simulated = 'None'
    cs_rms = 'None'
    cs_experimental = 'None'

    vbi.vbwSC.run_vbw(
        restart,
        number_of_structures,
        priors,
        structure_energies,
        number_of_measures,
        number_of_cs_measures,
        simulated,
        ncurves,
        experimental,
        output,
        nprocs,
        weight_cut,
        skip_vbw,
        cs_simulated,
        cs_rms,
        cs_experimental,
    )

    vbi.produce_final_output(output, file_list)

def process_variational(vbi_output_file, simulated_file, names_file, trm_simulated_file, trm_names_file, trm_priors_file):
    """

    :param vbi_output:
    :return:
    """

    intensities = read_file_safe(simulated_file)
    vbi_output = read_file_safe(vbi_output_file, skip_lines=5)
    last_output = vbi_output[-1][:-4]
    file_list = read_file_safe(names_file, 'unicode')

    nonzero_indexes = np.nonzero(last_output > 0.0)
    nonzeros = len(nonzero_indexes[0])
    output_intensities = intensities[:, nonzero_indexes[0]]
    output_filelist = file_list[last_output > 0.0]
    flat_weights = (1.0 / nonzeros) * np.ones(nonzeros)
    #print("Flat weights", flat_weights)
    savetext(trm_names_file, output_filelist)
    np.savetxt(trm_simulated_file, output_intensities)
    np.savetxt(trm_priors_file, flat_weights)


def run_complete(directory, simulated_file, priors_file, experimental_file, output_name, names_file):
    """

    :param simulated:
    :param priors:
    :param experimental:
    :param output_name:
    :param file_list:
    :param weight_cut:
    :return:
    """
    njobs = 1
    iterations = 2000
    chains = 1

    output_file = open(output_name,'w')
    # Files loading
    experimental = cbi.read_file_safe(experimental_file)
    simulated = cbi.read_file_safe(simulated_file)

    # Loading file names
    if names_file:
        file_names = cbi.read_file_safe(names_file, 'unicode')

    priors = cbi.read_file_safe(priors_file)

    fit = cbi.execute_stan(directory, experimental, simulated, priors,
                                   iterations, chains, njobs)

    bayesian_weights, jsd, crysol_chi2 = cbi.calculate_stats(fit, experimental, simulated)

    #fit_filemame = os.path.join(directory, 'fit.pkl')
    #with open(fit_filemame, "wb") as f:
    #    pickle.dump({'fit': fit}, f, protocol=-1)

    # Plotting
    import arviz
    import matplotlib
    matplotlib.use("Agg")
    axes = arviz.plot_density(fit, var_names=['weights'], show=None)
    fig = axes.ravel()[0].figure
    fig.savefig(os.path.join(directory, 'stan_weights.png'))

    #TODO: Write it to log somewhere
    for index, fname in enumerate(file_names):
        output_file.write((fname + ':' + str(bayesian_weights[index])) + '\n')
    output_file.write("JSD : " + str(jsd) + '\n')
    output_file.write("Chi2 :" + str(crysol_chi2) + '\n')


def run_bioce_from_webserver(params):
    experimental = os.path.join(params['study_folder'],params['dataset1'])
    pdb_files = os.path.join(params['study_folder'],params['dataset2'])
    #Standard file names
    file_list = os.path.join(params['analysis_folder'],'file_list.txt')
    simulated = os.path.join(params['analysis_folder'],'SimulatedIntensities.txt')
    priors = os.path.join(params['analysis_folder'],'weights.txt')
    #After running vbi
    vbi_simulated = os.path.join(params['analysis_folder'], 'vbi_SimulatedIntensities.txt')
    vbi_file_list = os.path.join(params['analysis_folder'],'vbi_file_list.txt')
    vbi_priors = os.path.join(params['analysis_folder'], 'vbi_weights.txt')
    vbi_output = os.path.join(params['output_folder'], 'vbi_output.txt')
    cbi_output = os.path.join(params['output_folder'], 'cbi_output.txt')
    job_done = True
    try:
        with zipfile.ZipFile(pdb_files, 'r') as zipObj:
            zipObj.extractall(params['analysis_folder'])
            pdb_list = zipObj.namelist()
        #number_of_structures = len(pdb_list)
    except:
        print("Failed to extact zipfile")
        job_done = False
        raise

    #maximum_cut = 0.01
    #winvert = 1.0/number_of_structures
    #weight_cut = winvert if winvert < maximum_cut else maximum_cut
    #TODO: This will come as parameter from simulatiom
    weight_cut = 0.05
    try:
        simulate_profiles(params['analysis_folder'], pdb_list, experimental)
    except:
        print("Failed to simulate profiles")
        job_done = False
        raise

    #simulated = 'SimulatedIntensitiesTest.txt'
    try:
        run_variational(simulated, priors, experimental, vbi_output, file_list, weight_cut)
        process_variational(vbi_output, simulated, file_list, vbi_simulated, vbi_file_list,  vbi_priors)
    except:
        print("Failed to perform Variational analysis")
        job_done = False
        raise

    try:
        run_complete(params['output_folder'], vbi_simulated, vbi_priors, experimental, cbi_output, vbi_file_list)
    except:
        print("Failed to perform Complete analysis")
        job_done = False
        raise

    return job_done

def run_bioce(params):
    pdb_files = params[0]
    simulated = params[1]
    priors = params[2]
    experimental = params[3]
    output = params[4]
    file_list = params[5]
    #We need to intrdduce some heuristic here

    job_done = True
    with zipfile.ZipFile(pdb_files, 'r') as zipObj:
        zipObj.extractall()
        pdb_list = zipObj.namelist()
    number_of_structures = len(pdb_list)
    maximum_cut = 0.01
    winvert = 1.0/number_of_structures
    weight_cut = winvert if winvert < maximum_cut else maximum_cut

    try:
        simulate_profiles(pdb_list, experimental)
    except:
        print("Failed to simulate profiles")
        job_done = False
        raise

    #simulated = 'SimulatedIntensitiesTest.txt'
    try:
        run_variational(simulated, priors, experimental, 'vbi_'+output, file_list, weight_cut)
        simulated, priors, file_list = process_variational('vbi_'+output, simulated, priors, file_list)
    except:
        print("Failed to perform Variational analysis")
        job_done = False
        raise

    try:
        run_complete(simulated, priors, experimental, 'cbi_'+output, file_list)
    except:
        print("Failed to perform Complete analysis")
        job_done = False
        raise

    return job_done

if __name__ == "__main__":
    pdb_files = 'pdbs.zip'
    simulated = 'SimulatedIntensities.txt'
    priors = 'weights.txt'
    experimental = 'experimental_test.dat'
    output = 'output.txt'
    file_list = 'file_list'
    params = [pdb_files,simulated,priors,experimental,output,file_list]
    job_done = run_bioce(params)