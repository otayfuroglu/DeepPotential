# Removes unfinished frames from the CSV so that the next job picks them up again
# and continues from their .chk file (SCF=Restart).
# Use it ONLY when no job is running on this input file.
#
# Logic (with -rm_out_dir yes):
#   - frame directory deleted: finished (or Gaussian error) -> stays in the CSV
#   - frame directory exists, but its log has no "Normal termination": interrupted -> removed from the CSV
import os
import pandas as pd

name = 'bulk_h2o_box_nequip_20K_nvt_AL_iter10_falsepbc'
csv, run = f'engrad_{name}.csv', f'run_engrad_{name}'

df = pd.read_csv(csv)

def unfinished(lbl):
    d = os.path.join(run, lbl)
    if not os.path.isdir(d):
        return False
    log = os.path.join(d, f'{lbl}.log')
    return not (os.path.exists(log) and 'Normal termination' in open(log, errors='ignore').read())

mask = df['FileNames'].apply(unfinished)
df.to_csv(csv + '.bak', index=None)
df[~mask].to_csv(csv, index=None)
print(f'{len(df)} entries: {mask.sum()} unfinished removed, {len(df) - mask.sum()} kept')
print(f'Backup of the old CSV: {csv}.bak')
