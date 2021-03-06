import os
import sys
import numpy as np
import shlex
from subprocess import Popen, PIPE


def read_file_safe(filename, skip_lines, dtype="float64"):
    """
    Simple check if file exists
    :param filename:
    :return:
    """
    try:
        results = np.genfromtxt(filename, dtype=dtype, skip_header=skip_lines)
    except IOError as err:
        print(os.strerror(err.errno))
    return results


def process_pdbs_with_experimental(directory, pdb_list, experimental_file):
    intensities = None
    #experimental_file = os.path.join(directory, experimental_file)
    for pdb_file in pdb_list:
        #Skipping non-PDB files - may not be best solution though
        pdb_filename = os.path.join(directory,pdb_file.strip("\n"))
        if pdb_filename[-3:] != 'pdb':
            continue
        cmd_line = (
            "Pepsi-SAXS "
            + pdb_filename
            + " "
            + experimental_file
            + " -o "+pdb_filename+'.fit'
        )
        print(cmd_line)
        proc = Popen(shlex.split(cmd_line), stdout=PIPE, shell=False)
        os.waitpid(proc.pid, 0)
        (out, err) = proc.communicate()
        data = read_file_safe(pdb_filename+ ".fit", 6)
        intensity = data[:, 3]
        qvector = data[:, 0]
        log_file = open(pdb_filename+ ".log")
        #TODO: Better solution should be found here
        log_data = log_file.readlines()
        log_data_line1 = log_data[62]
        log_data_line2 = log_data[63]
        log_file.close()
        if log_data_line1[:7] == "Scaling":
            scaling_factor = float(log_data_line1.split(":")[1])
        elif log_data_line2[:7] == "Scaling":
            scaling_factor = float(log_data_line2.split(":")[1])
        else:
            raise Exception("Sorry cannot simulate scattering profiles")
        intensity /= scaling_factor
        if intensities is None:
            intensities = intensity
        else:
            intensities = np.c_[intensities, intensity]
    return intensities


def add_errors_m(intensities, qvector):
    k = 4700
    c = 0.85
    q_arb = 0.2
    mult_fact = 100
    tau = 1
    I_0 = intensities[0]
    I_Q = intensities * mult_fact / I_0
    sigma = np.sqrt((1 / (k * qvector)) * (I_Q) * tau)
    idx = (np.abs(qvector - q_arb)).argmin()
    addon = np.sqrt((1 / (k * qvector[idx])) * 2 * c * I_Q[idx] / (1 - c)) * tau
    sigma += addon
    # I_Q_E = np.rnorm(len(qvector),I_Q*I_0/mult_fact,sigma*I_0/mult_fact)
    return sigma * I_0 / mult_fact


def generate_file_list(directory, pdb_list):
    flist_file = os.path.join(directory,'file_list.txt')
    f = open(flist_file, "w")
    line_to_write = " ".join(pdb_list)
    f.writelines(line_to_write)
    f.close()


def generate_weights(directory, pdb_list):
    wfile = os.path.join(directory,'weights.txt')
    out = open(wfile, "w")
    len_models = len(pdb_list)
    fwght = 1.0 / (len_models)
    for i in range(len_models):
        out.write(str(fwght) + " ")
    out.close()


if __name__ == "__main__":
    pdb_list_name = sys.argv[1]
    pdb_list = open(pdb_list_name).readlines()
    pdb_list = [pdb.strip() for pdb in pdb_list]
    output_directory = './'
    experimental_file = sys.argv[2]
    generate_file_list(output_directory, pdb_list)
    generate_weights(output_directory, pdb_list)
    intensities = process_pdbs_with_experimental(output_directory, pdb_list, experimental_file)
    np.savetxt("SimulatedIntensities.txt", intensities)
