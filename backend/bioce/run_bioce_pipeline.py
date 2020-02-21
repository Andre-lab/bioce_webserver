"""
Pipeline for running BIOCE from raw pdb file and saxs data
"""
from preparePepsi import (
    generate_file_list,
    generate_weights,
    process_pdbs_with_experimental,
)
import variationalBayesian as vbi
import fullBayesian as cbi
import numpy as np
import os


def read_file_safe(filename, dtype="float64"):
    """
    Simple check if file exists
    :param filename:
    :return:
    """
    try:
        results = np.genfromtxt(filename, dtype=dtype)
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

def simulate_profiles(pdb_list_name, experimental_filename):
    """

    :param pdb_list_name:
    :param experimental_filename:
    :return:
    """
    pdb_list = open(pdb_list_name).readlines()
    experimental_file = experimental_filename
    generate_file_list(pdb_list_name)
    generate_weights(pdb_list_name)
    intensities = process_pdbs_with_experimental(pdb_list, experimental_file)
    # TODO: Change locations to Analysis software
    np.savetxt("SimulatedIntensities.txt", intensities)


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
    structure_energies = None
    nprocs = 4
    skip_vbw = 0
    cs_simulated = None
    cs_rms = None
    cs_experimental = None

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

def process_variational(vbi_output):
    """

    :param vbi_output:
    :return:
    """

    simulated_file = 'SimulatedIntensities.txt'
    names_file = 'FileNamesVBI.txt'
    intensities = read_file_safe(simulated_file])
    vbi_output = read_file_safe(sys.argv[1])
    last_output = vbi_output[-1][:-4]
    file_list = read_file_safe(sys.argv[3], 'unicode')

    nonzero_indexes = np.nonzero(last_output > 0.0)
    print(nonzero_indexes)

    output_intensities = intensities[:, nonzero_indexes[0]]
    output_filelist = file_list[last_output > 0.0]

    savetext('file_sub.txt', output_filelist)
    np.savetxt(simulated_file, output_intensities)

    return simulated_file, priors_file, names_file

def run_complete(simulated_file, priors_file, experimental_file, output_name, names_file):
    """

    :param simulated:
    :param priors:
    :param experimental:
    :param output_name:
    :param file_list:
    :param weight_cut:
    :return:
    """
    njobs = 4
    iterations = 2000
    chains = 4

    output_file = open(output_name)
    # Files loading
    experimental = cbi.read_file_safe(experimental_file)
    simulated = cbi.read_file_safe(simulated_file)

    # Loading file names
    if names_file:
        file_names = cbi.read_file_safe(names_file, 'unicode')

    priors = cbi.read_file_safe(priors_file)

    fit = cbi.execute_stan(experimental, simulated, priors,
                                   iterations, chains, njobs)


    bayesian_weights, jsd, crysol_chi2 = cbi.calculate_stats(fit, experimental, simulated)
    #TODO: Write it to log somewhere
    for index, fname in enumerate(file_names):
                output_file.write((fname, bayesian_weights[index]))
    print("JSD: " + str(jsd))
    print("Chi2 SAXS:" + str(crysol_chi2))


if __name__ == "__main__":
    pdb_files = 'pdbs.zip'
    simulated = 'SimulatedIntensities.txt'
    priors = 'flat_wghts.txt'
    experimental = 'experimental.dat'
    output = 'output.txt'
    file_list = 'file_list'
    #We need to intrdduce some heuristic here
    weight_cut = 0.1

    simulate_profiles(pdb_files, experimental)
    run_variational(simulated, priors, experimental, output, file_list, weight_cut)
    process_varitional()
    run_complete()
