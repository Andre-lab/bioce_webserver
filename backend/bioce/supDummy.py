from os.path import dirname, abspath
base = dirname(dirname(abspath(__file__)))
import freesas
from freesas.align import InputModels, AlignModels


def supycomb(file_list):
    """main application"""
    description = "Aligns models pairwise and calculates NSD"
    epilog = """ Adapted from supycomb from freesas. Aligining all mo
    """
    slow = True
    enantiomorphs = True
    save = True

    reference = file_list[0]
    for target in file_list[1:]:
        align = AlignModels([reference, target], slow=slow, enantiomorphs=enantiomorphs)
        align.outputfiles = f'aligned_{target}'
        align.assign_models()
        dist = align.alignment_2models()
        print(f"NSD distance: {dist}")

if __name__ == "__main__":
    file_list = []
    supycomb(file_list)