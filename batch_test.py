from multiprocessing import Pool

from os import listdir
import subprocess


def call_command(file_name):
    output_file = f"output/scn_{file_name}.csv"
    cmdstr = f"BlueSky.py --detached --scenfile /home/viethoangcr/Documents/Workspace/bluesky/scenario/TP_test/" \
             f"{file_name} --log-output {output_file}"
    print(f"Executing cmd {cmdstr}")
    p = subprocess.call(["python", *cmdstr.split()])
    print(f"DOne executing cmd {cmdstr}: {p}")
    return p


if __name__ == "__main__":
    file_list = [fn for fn in listdir('scenario/TP_test') if fn.endswith('.scn')]
    with Pool(6) as p:
        res = p.map(call_command, file_list)
