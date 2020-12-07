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
import shutil
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

def combine_models(directory, data_labels):
    """
    Combines all avaialable models from output directory
    :param directory:
    :return:
    """
    output_filename = os.path.join(directory, 'ensemble.pdb')
    output_file = open(output_filename, 'w')
    for index, filename in enumerate(data_labels):
        output_file.write('MODEL '+str(index)+'\n')
        file_path = os.path.join(directory,filename)
        lines = open(file_path).readlines()
        output_file.writelines(lines)
        output_file.write('ENDMDL')
    output_file.close()

def plot_weights(directory, data_labels, fit):
    """

    :param directory:
    :param data_labels:
    :param fit:
    :return:
    """
    import matplotlib
    import matplotlib.pyplot as plt
    import seaborn as sns
    matplotlib.use("Agg")

    #Pytsan native solution - deprecated
    #fig = fit.plot(pars="weights")
    #ax.set_color_cycle(['red', 'black', 'yellow', 'green', 'blue'])
    #fig.subplots_adjust(wspace=0.8)
    #fig.savefig(os.path.join(directory, 'stan_weights.png'))

    #Arviz solution
    fit_df = fit.to_dataframe()
    #axes = arviz.plot_density(fit, var_names=['weights'], show=None)
    #fig = axes.ravel()[0].figure
    for index, data_name in enumerate(data_labels):
        plt.figure()
        sns.kdeplot(fit_df['weights['+str(index+1)+']'])
        plt.ylabel('Frequency')
        plt.savefig(os.path.join(directory, 'stan_weight_'+data_name+'.png'))

def plot_fit(directory, chi2):
    """

    :param directory:
    :param data_labels:
    :param fit:
    :param chi2:
    :return:
    """
    import matplotlib
    import matplotlib.pyplot as plt
    matplotlib.use("Agg")

    fit_file = os.path.join(directory,'cbi_output.txt.fit')
    data = read_file_safe(fit_file)
    qvector = data[:,0]
    exp_intensities = data[:,1]
    sim_intensities = data[:,2]
    exp_errors = data[:,3]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(qvector, exp_intensities, 'ko', markersize=4, mfc="none", label="experimental")
    plt.plot(qvector, sim_intensities, '-o', markersize=4, label="fit")
    plt.errorbar(qvector, exp_intensities, yerr=exp_errors,
                 fmt="ko", markersize=6, mfc='none', alpha=0.6, zorder=0)

    plt.yscale('log')
    plt.ylabel("$Intenisty$")
    plt.xlabel("$q [\AA^{-1}]$")
    plt.text(0.8,0.8,r'$\chi^2 = $'+str(round(chi2,2)), transform=ax.transAxes)
    fig.savefig(os.path.join(directory, 'fit.png'))

def save_selected_pdbfiles(analysis_directory, output_directory, data_labels):
    """

    :param analysis_directory:
    :param output_directory:
    :param data_labels:
    :return:
    """

    for fname in data_labels:
        src_file = os.path.join(analysis_directory, fname)
        dest_file = os.path.join(output_directory, fname)
        shutil.copyfile(src_file, dest_file)

def run_complete(output_directory, analysis_directory, simulated_file, priors_file, experimental_file,
                 output_name, names_file, iterations):
    """

    :param output_directory:
    :param analysis_directory:
    :param simulated_file:
    :param priors_file:
    :param experimental_file:
    :param output_name:
    :param names_file:
    :param iterations:
    :return:
    """
    njobs = 1
    chains = 4

    output_file = open(output_name,'w')
    # Files loading
    experimental = cbi.read_file_safe(experimental_file)
    simulated = cbi.read_file_safe(simulated_file)

    # Loading file names
    if names_file:
        file_names = cbi.read_file_safe(names_file, 'unicode')

    priors = cbi.read_file_safe(priors_file)

    fit = cbi.execute_stan(output_directory, experimental, simulated, priors,
                                   iterations, chains, njobs)

    bayesian_weights, bayesian_sem, bayesian_sd, bayesian_neff, bayesian_rhat, jsd, crysol_chi2, corrmap = \
        cbi.calculate_stats(output_directory, fit, experimental, simulated)

    model_evidence = cbi.calculate_model_evidence(experimental, simulated, priors)

    #TODO: Write it to log somewhere
    data_labels = []
    for index, fname in enumerate(file_names):
        output_file.write(fname + ':' + str(bayesian_weights[index]) + ':' + str(bayesian_sem[index])
                          + ':' + str(bayesian_sd[index]) + ':' + str(bayesian_neff[index])
                          + ':' + str(bayesian_rhat[index]) + '\n')
        data_labels.append(fname)
    output_file.write("JSD : " + str(jsd) + '\n')
    output_file.write("Chi2 : " + str(crysol_chi2) + '\n')
    output_file.write("Model Evidence : " + str(model_evidence) + '\n')
    output_file.write("Cormap : " + str(corrmap) + '\n')
    output_file.close()

    save_selected_pdbfiles(analysis_directory, output_directory, data_labels)
    combine_models(output_directory, data_labels)
    plot_weights(output_directory, data_labels, fit)
    plot_fit(output_directory, crysol_chi2)

def run_bioce_from_webserver(params, weight_cut, iterations):
    experimental = os.path.join(params['study_folder'],params['dataset1'])
    pdb_files = os.path.join(params['study_folder'],params['dataset2'])
    #Standard file names
    file_list = os.path.join(params['analysis_folder'],'file_list.txt')
    simulated_custom_file = params['dataset3'] if 'dataset3' in params else None
    if simulated_custom_file:
        simulated = os.path.join(params['study_folder'], simulated_custom_file)
    else:
        simulated = os.path.join(params['analysis_folder'],'SimulatedIntensities.txt')

    priors = os.path.join(params['analysis_folder'],'weights.txt')
    #After running vbi
    vbi_simulated = os.path.join(params['analysis_folder'], 'vbi_SimulatedIntensities.txt')
    vbi_file_list = os.path.join(params['analysis_folder'],'vbi_file_list.txt')
    vbi_priors = os.path.join(params['analysis_folder'], 'vbi_weights.txt')
    vbi_output = os.path.join(params['output_folder'], 'vbi_output.txt')
    cbi_output = os.path.join(params['output_folder'], 'cbi_output.txt')
    job_done = True
    pdb_list = []
    try:
        with zipfile.ZipFile(pdb_files, 'r') as zipObj:
            for zip_info in zipObj.infolist():
                if zip_info.filename.startswith('__MACOSX/') or zip_info.filename[-1] == '/':
                    continue
                zip_info.filename = os.path.basename(zip_info.filename)
                zipObj.extract(zip_info, params['analysis_folder'])
                pdb_list.append(zip_info.filename)
    except:
        print("Failed to extact zipfile")
        job_done = False
        raise

    #TODO: Skip this step if simulated profiles are provided

    try:
        generate_file_list(params['analysis_folder'], pdb_list)
        generate_weights(params['analysis_folder'], pdb_list)
        if simulated_custom_file is None:
            simulate_profiles(params['analysis_folder'], pdb_list, experimental)
        else:
            print('Using custom simulated SAS profiles')
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
        run_complete(params['output_folder'], params['analysis_folder'],
                     vbi_simulated, vbi_priors, experimental, cbi_output,
                     vbi_file_list, iterations)
    except:
        print("Failed to perform Complete analysis")
        job_done = False
        raise

    return job_done

def run_bioce(params, weight_cut, iterations):
    pdb_files = params['pdb_file']
    simulated = params['simulated']
    simulated_custom_file = params['simulated_custom']
    priors = params['priors']
    experimental = params['experimental']
    file_list = params['file_list']
    #We need to intrdduce some heuristic here

    vbi_simulated = os.path.join(params['analysis_folder'], 'vbi_SimulatedIntensities.txt')
    vbi_file_list = os.path.join(params['analysis_folder'], 'vbi_file_list.txt')
    vbi_priors = os.path.join(params['analysis_folder'], 'vbi_weights.txt')
    vbi_output = os.path.join(params['output_folder'], 'vbi_output.txt')
    cbi_output = os.path.join(params['output_folder'], 'cbi_output.txt')
    job_done = True
    pdb_list = []

    try:
        with zipfile.ZipFile(pdb_files, 'r') as zipObj:
            for zip_info in zipObj.infolist():
                if zip_info.filename.startswith('__MACOSX/') or zip_info.filename[-1] == '/':
                    continue
                zip_info.filename = os.path.basename(zip_info.filename)
                zipObj.extract(zip_info, params['analysis_folder'])
                pdb_list.append(zip_info.filename)
    except:
        print("Failed to extract zipfile")
        job_done = False
        raise

    # TODO: Skip this step if simulated profiles are provided

    try:
        generate_file_list(params['analysis_folder'], pdb_list)
        generate_weights(params['analysis_folder'], pdb_list)
        if simulated_custom_file is None:
            simulate_profiles(params['analysis_folder'], pdb_list, experimental)
        else:
            print('Using custom simulated SAS profiles')
    except:
        print("Failed to simulate profiles")
        job_done = False
        raise

    # simulated = 'SimulatedIntensitiesTest.txt'
    try:
        run_variational(simulated, priors, experimental, vbi_output, file_list, weight_cut)
        process_variational(vbi_output, simulated, file_list, vbi_simulated, vbi_file_list, vbi_priors)
    except:
        print("Failed to perform Variational analysis")
        job_done = False
        raise

    try:
        run_complete(params['output_folder'], params['analysis_folder'],
                     vbi_simulated, vbi_priors, experimental, cbi_output,
                     vbi_file_list, iterations)
    except:
        print("Failed to perform Complete analysis")
        job_done = False
        raise

    return job_done


if __name__ == "__main__":
    params = {}
    params['pdb_files'] = 'pdbs.zip'
    params['simulated'] = 'SimulatedIntensities.txt'
    params['simulated_custom'] = None
    params['priors'] = 'weights.txt'
    params['experimental'] = 'experimental_test.dat'
    params['file_list'] = 'file_list'

    params['analysis_folder'] ='analysis_folder'
    params['output_folder'] = 'output_folder'
    weight_cutoff = 0.01
    iterations = 2000
    job_done = run_bioce(params, weight_cutoff, iterations)
