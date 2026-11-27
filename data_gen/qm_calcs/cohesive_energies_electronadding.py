from ase import Atoms
from ase.io import write, read
from ase.calculators.singlepoint import SinglePointCalculator
import argparse

import json



def substractSelfEnergy(atoms):
    total_self_energy = 0
    for symbol in symbols_selfenergy_pair.keys():
        num_atoms = len([atom for atom in atoms if atom.symbol == symbol])
        self_energy = num_atoms * float(symbols_selfenergy_pair[symbol])
        total_self_energy += self_energy
    return total_self_energy

#  atomic_energies={"C": "-1025.34896263954",
#                   "O": "-2034.97553102427",
#                   "H": "-13.5576149854593",
#                   "Mg": "-1479.90402789208",
#                  }
#
#  symbols = ['C', 'O', 'H', 'Mg']
#


parser = argparse.ArgumentParser(description="Give something ...")
parser.add_argument("-extxyz_path", type=str, required=True, help="..")
parser.add_argument("-symbols_selfenergy_pair", type=str, required=True, help="")
parser.add_argument("-electron_energy", type=float, default=-13.68196853283535,
                    help="Energy of one electron (eV) used for charged frames")
args = parser.parse_args()

electron_energy = args.electron_energy

extxyz_path = args.extxyz_path
symbols_selfenergy_pair = json.loads(args.symbols_selfenergy_pair)

atoms_list = read(extxyz_path, index=":")

# check every frame first so no partial output is written
for idx, atoms in enumerate(atoms_list):
    # frames without total_charge are treated as neutral
    total_charge = int(atoms.info.get("total_charge", 0))
    if abs(total_charge) > 1:
        label = atoms.info.get("label", idx)
        raise ValueError(f"Frame {label}: total_charge={total_charge}, "
                         "only -1, 0 and +1 are supported")

for atoms in atoms_list:
    total_charge = int(atoms.info.get("total_charge", 0))
    total_energy = atoms.get_potential_energy()
    self_energy = substractSelfEnergy(atoms)
    
    # correction for self_e: +electron_energy for -1, -electron_energy for +1
    self_energy -= total_charge * electron_energy

    cohesive_energy = total_energy-self_energy

    atoms.calc = SinglePointCalculator(atoms, energy=cohesive_energy, forces=atoms.get_forces())
    atoms.get_potential_energy()
    write(f"cohesive_{extxyz_path.split('/')[-1]}", atoms, append=True)

