import os
import sys
import optparse
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


def extract_scattering_profiles(dir_name):
    file_list = os.listdir(dir_name)
    experimental_int = None
    print(file_list)
    #TODO: Gasbor different than dammif
    for fir_file in file_list:
        if '.fir' in fir_file:
            data = read_file_safe(os.path.join(dir_name, fir_file), 1)
            print(np.shape(data))
            experimental_int = data[:, -1] if experimental_int is None else np.c_[
                experimental_int, data[:, -1]]
    return experimental_int

if __name__ == "__main__":
    doc = """
            Script to generate scattering curves from pdb files
        """
    print(doc)
    usage = "usage: %prog [options] args"

    option_parser_class = optparse.OptionParser
    parser = option_parser_class(usage=usage, version='0.1')
    parser.add_option("-s", "--structure_library", dest="dir_name",
                      help="Directory containing pdb files [OBLIGATORY]")
    parser.add_option("-e", "--experimental", dest="exp_file",
                      help="Experimental SAXS curves [OBLIGATORY]")
    options, args = parser.parse_args()
    out_file = open("SimulatedIntensities.txt", "w")
    intensities = extract_scattering_profiles(options.dir_name)
    np.savetxt(out_file, intensities)