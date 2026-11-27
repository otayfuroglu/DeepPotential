from ase.io import write, read
import numpy as np
import argparse
#atoms_list = read("cohesive_isole_explicit_13kNNP_100K_50K_16946.extxyz", index=":")


parser = argparse.ArgumentParser(description="Remove structures with large forces using continue")
parser.add_argument("-in_extxyz", type=str, required=True)
parser.add_argument("-out_extxyz", type=str, default="filtered.extxyz", help="Output extxyz without large forces")
args = parser.parse_args()

in_extxyz = args.in_extxyz
out_extxyz = args.out_extxyz

with open(f"{in_extxyz.split('/')[-1].split('.')[0].replace('sp_', '')}_forces.csv", "w") as fl:
    print("Label, Force", file=fl)

    #filtered_structures = []

    for atoms in read(in_extxyz, index=":"):
        label = atoms.info["label"]
        forces = np.array(atoms.get_forces())
        if np.any(np.abs(forces) > 100):
            continue
        write(out_extxyz, atoms, append= True)
        for force in forces.flatten():
            print(label, force, file=fl)
        # print(f"{len(filtered_structures)} structures written to {out_extxyz}")

