from freesas.align import InputModels, AlignModels
import os
import shutil

def supcomb_models(output_directory, file_list):
    """main application"""
    description = "Aligns models pairwise and calculates NSD"
    epilog = """ Adapted from supycomb from freesas. Aligining all mo
    """
    slow = True
    enantiomorphs = True
    save = True

    reference = file_list[0]
    src_file = os.path.join(output_directory, reference)
    aligned_data_labels =  [f'aligned_{reference}']
    dest_file = os.path.join(output_directory, f'aligned_{reference}')

    shutil.copyfile(src_file, dest_file)
    for target in file_list[1:]:
        target_file = os.path.join(output_directory, target)
        aligned_data_labels.append(f'aligned_{target}')
        align = AlignModels([src_file, target_file], slow=slow, enantiomorphs=enantiomorphs)
        align.outputfiles = os.path.join(output_directory,f'aligned_{target}')
        align.assign_models()
        dist = align.alignment_2models()
        print(f"NSD distance between: {reference} and {target} : {dist}")
    return aligned_data_labels


if __name__ == "__main__":
    file_list = ['StaticDimer_abs-1.pdb', 'StaticDimer_abs-2.pdb','StaticDimer_abs-3.pdb','StaticDimer_abs-4.pdb', ]
    supcomb_models(file_list)