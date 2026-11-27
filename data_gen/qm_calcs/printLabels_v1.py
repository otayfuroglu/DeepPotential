#
from ase.io import read, write
import argparse

parser = argparse.ArgumentParser(description="Give something ...")
parser.add_argument("-in_extxyz", type=str, required=True)
args = parser.parse_args()


in_extxyz = args.in_extxyz

with open(f"{in_extxyz.split('/')[-1].split('.')[0].replace('sp_', '')}_labels.csv", "w") as fl:
    print("Label", file=fl)
             
    for atoms in read(in_extxyz, index=":"):

        label = atoms.info.get("label")
        print(f"{label}", file=fl)
