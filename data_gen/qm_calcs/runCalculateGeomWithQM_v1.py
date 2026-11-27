#!/usr/bin/env python
import argparse
import os
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calculateGeomWithQM as cg
from ase.calculators.gaussian import Gaussian
from ase.calculators.orca import ORCA, OrcaProfile


CFG = {}
CHARGE_MAP = {}
MULT_MAP = {}


def g16Calculator(label, n_task):
    route = "#"
    if CFG["calc_type"] == "engrad":
        route += " Force"
    if CFG["guess_mix"]:
        route += " Guess=Mix"
    if CFG["solvent"]:
        route += f" SCRF=({CFG['solvent_model']}, solvent={CFG['solvent']})"

    link0 = {}
    if CFG["g16_chk"]:
        link0 = dict(chk=f"{label}.chk", save=None)

    return Gaussian(
        label=label,
        mem=CFG["mem"],
        nprocshared=n_task,
        xc=CFG["xc"],
        basis=CFG["basis"],
        scf="maxcycle=100",
        charge=CHARGE_MAP[label],
        mult=MULT_MAP[label],
        pop="MK, Hirshfeld",
        extra=route,
        addsec=None,
        **link0,
    )


def orca_calculator(orca_path, base, calc_type, n_task, initial_gbw=['', '']):
    simple = (f"{calc_type.upper()} {CFG['orca_method']} MINIPRINT NOPRINTMOS "
              f"NoKeepInts NOKEEPDENS CHELPG AIM {initial_gbw[0]}")
    scf = "%scf Convergence tight \n maxiter 250"
    if CFG["orca_autotrah"]:
        scf += f" \n AutoTRAHIter {CFG['orca_autotrah']}"
    blocks = (f"{scf} end \n %output \n Print[ P_Hirshfeld] 1 end \n"
              f" %pal nprocs {n_task} end")
    if CFG["orca_maxcore"]:
        blocks += f" \n %maxcore {CFG['orca_maxcore']}"

    if CFG["solvent"]:
        simple += f" CPCM({CFG['solvent']})"
        if CFG["solvent_model"].upper() == "SMD":
            blocks += f'\n%cpcm smd true \n SMDsolvent "{CFG["solvent"]}" end'

    blocks += initial_gbw[1]

    return ORCA(
        profile=OrcaProfile(orca_path),
        charge=CHARGE_MAP[base], mult=MULT_MAP[base],
        orcasimpleinput=simple,
        orcablocks=blocks,
    )


def install_calculators():
    """Replace the calculator factories of the original module with ours."""
    cg.g16Calculator = g16Calculator
    cg.orca_calculator = orca_calculator


def str2bool(v):
    return str(v).lower() in ("yes", "true", "1", "y")


def resolve(atoms, value, key, default):
    """'auto' -> atoms.info[key] (or default), otherwise the given integer."""
    if str(value).lower() == "auto":
        return int(atoms.info.get(key, default))
    return int(value)


def make_tag(calculator, calc_type, solvent, solvent_model):
    solv = "gas" if not solvent else f"{solvent_model.lower()}-{solvent.lower()}"
    return f"{calculator}_{calc_type}_{solv}"


def main():
    p = argparse.ArgumentParser(description="Batch g16/ORCA calculations with ASE")

    # input / output
    p.add_argument("-in_extxyz", required=True)
    p.add_argument("-out_extxyz", default=None,
                   help="Default: <input>_<tag>.extxyz")
    p.add_argument("-csv", default=None,
                   help="Default: calculated_<input>.csv")
    p.add_argument("-work_dir", default=None,
                   help="Default: ./<tag>  (one directory per setting)")
    p.add_argument("-rm_out_dir", default="yes")

    # calculation type
    p.add_argument("-calculator_type", default="g16", choices=["g16", "orca"])
    p.add_argument("-calc_type", default="engrad", choices=["engrad", "sp"])

    # resources
    p.add_argument("-n_core", type=int, default=1, help="Total number of cores")
    p.add_argument("-n_proc", type=int, default=1,
                   help="Parallel jobs (each uses n_core/n_proc cores)")
    p.add_argument("-mem", default="20GB", help="Memory per job (g16)")

    # charge / mult
    p.add_argument("-charge", default="auto",
                   help="'auto' (from extxyz info, else 0) or an integer")
    p.add_argument("-charge_key", default="total_charge")
    p.add_argument("-mult", default="1",
                   help="'auto' (from extxyz info, else 1) or an integer")
    p.add_argument("-mult_key", default="mult")
    p.add_argument("-guess_mix", default="no",
                   help="Add Guess=Mix for g16 (open-shell / radicals)")
    p.add_argument("-g16_chk", default="no",
                   help="Keep <label>.chk for each g16 job")

    # solvent
    p.add_argument("-solvent", default="none",
                   help="none | water | n-octanol | ...")
    p.add_argument("-solvent_model", default="SMD",
                   choices=["SMD", "PCM", "CPCM"])

    # level of theory
    p.add_argument("-xc", default="wb97xd")
    p.add_argument("-basis", default="6-311++G(3df,3pd)")
    p.add_argument("-orca_path", default=os.environ.get("ORCA_PATH")
                   or shutil.which("orca") or "orca")
    p.add_argument("-orca_method", default="PBE D4 DEF2-TZVP DEF2/J RIJDX")
    p.add_argument("-orca_maxcore", type=int, default=None,
                   help="ORCA %%maxcore in MB per core (e.g. 2200)")
    p.add_argument("-orca_autotrah", type=int, default=None,
                   help="ORCA AutoTRAHIter in the %%scf block (e.g. 70)")

    # run order
    p.add_argument("-shuffle", default="no",
                   help="Process frames in random order (several jobs on one input)")

    a = p.parse_args()

    solvent = None if a.solvent.lower() in ("none", "gas", "") else a.solvent
    calculator = a.calculator_type.lower()
    calc_type = a.calc_type.lower()
    n_task = max(1, a.n_core // a.n_proc)

    CFG.update(calc_type=calc_type, solvent=solvent,
               solvent_model=a.solvent_model, mem=a.mem,
               guess_mix=str2bool(a.guess_mix), g16_chk=str2bool(a.g16_chk),
               orca_maxcore=a.orca_maxcore, orca_autotrah=a.orca_autotrah,
               xc=a.xc, basis=a.basis, orca_method=a.orca_method)

    in_path = Path(a.in_extxyz).resolve()
    stem = in_path.stem
    tag = make_tag(calculator, calc_type, solvent, a.solvent_model)

    work_dir = Path(a.work_dir or tag).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    out_extxyz = work_dir / (a.out_extxyz or f"{stem}_{tag}.extxyz")
    csv_path = work_dir / (a.csv or f"calculated_{stem}.csv")

    install_calculators()

    job = cg.CaculateData(
        orca_path=a.orca_path,
        calc_type=calc_type,
        calculator_type=calculator,
        n_task=n_task,
        in_extxyz_path=str(in_path),
        out_extxyz_path=str(out_extxyz),
        csv_path=str(csv_path),
        base_dir=str(work_dir),
        rm_out_dir=str2bool(a.rm_out_dir),
    )

    charges = []
    for idx, atoms in enumerate(job.atoms_list):
        label = atoms.info.get("label", "frame_" + "{0:0>5}".format(idx))
        atoms.info["label"] = label
        q = resolve(atoms, a.charge, a.charge_key, 0)
        m = resolve(atoms, a.mult, a.mult_key, 1)
        CHARGE_MAP[label], MULT_MAP[label] = q, m
        # keep the level of theory in the output extxyz
        atoms.info["qm_charge"], atoms.info["qm_mult"] = q, m
        atoms.info["qm_level"] = tag
        charges.append(q)

    # labels are already fixed above, so reordering does not change them
    if str2bool(a.shuffle):
        random.shuffle(job.atoms_list)

    print("=" * 60)
    print(f" Input        : {in_path}")
    print(f" Level (tag)  : {tag}")
    print(f" Method       : {a.xc}/{a.basis}" if calculator == "g16"
          else f" Method       : {a.orca_method}")
    print(f" Charge mode  : {a.charge} (key={a.charge_key}) "
          f"-> {sorted(set(charges))}")
    print(f" Mult mode    : {a.mult}  (guess_mix={CFG['guess_mix']})")
    print(f" Frames       : {len(job.atoms_list)}")
    print(f" Cores        : {a.n_proc} x {n_task}  (mem/job={a.mem})")
    print(f" Work dir     : {work_dir}")
    print(f" Output       : {out_extxyz}")
    print("=" * 60, flush=True)

    job.calculate_data(n_proc=a.n_proc)


if __name__ == "__main__":
    main()
