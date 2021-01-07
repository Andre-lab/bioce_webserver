"""
Reads in "*.fir" files and store them in the simulated intesnity file.
It also extracts experimental file for the same q vector
"""

import os
import sys
import numpy as np

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

def combine_intensities(fir_list):
    fir_array = []
    for fir_file in fir_list:
        fir_file = fir_file.strip('\n')
        if fir_file[-3:] == 'fir':
            data = read_file_safe(fir_file, 1)
            fir_array.append(data[:,4])
    np.savetxt('SimulatedIntensities.dat', np.transpose(fir_array))

def setup_exp_file(fir_list):
    fir_file = fir_list[0]
    fir_file = fir_file.strip('\n')
    data = read_file_safe(fir_file, 1)
    q_data = data[:,0]
    int_data = data[:, 1]
    err_data = data[:, 2]
    np.savetxt('Experimental.dat',  np.c_[q_data, int_data, err_data])

if __name__ == "__main__":
    fir_list = open(sys.argv[1]).readlines()
    combine_intensities(fir_list)
    setup_exp_file(fir_list)