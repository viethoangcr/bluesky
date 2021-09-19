"""
Airspace Design Contest Scenario Generator:

Draw circles and runways in use
Generate traffic at edges and at airports
Make sure scenario can be saved

"""

from bluesky import core, stack, traf, sim, tools, navdb  # , settings, navdb, traf, sim, scr, tools
from bluesky.tools import datalog

from adsb_converter import read_space_based_adsb, split_flight, generate_scenario

import numpy as np
from pathlib import Path
# import heapq

np.random.seed(7)
db = None
file_path = Path('/home/viethoangcr/Documents/Dataset/Dataset/ADSB_SPACE_BASED_TRACKS_2020_02.csv.gz')


def init_plugin():
    print("Initialising logging plugin")
    global db
    db = AdsbDataset(file_path, nrows=200000)

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name': 'ADSB_MCRE',
        'plugin_type': 'sim',
        'udpate_interval': 0.1,
        'preupdate': db.update,
        'reset': db.reset,
    }

    stackfunctions = {
        "AMCRE": [
            "AMCRE n",
            "int",
            db.mcre,
            "Multiple random create of n aircraft using historical ADSB data",
        ],
    }

    return config, stackfunctions


class AdsbDataset(core.Entity):
    ''' Loading datababse. '''

    def __init__(self, file_path, nrows=None):
        super().__init__()
        print(f"Loading ADSB data file {file_path}")
        proccessed_df = read_space_based_adsb(file_path, nrows=nrows)
        self.flights = split_flight(proccessed_df, min_points=100, min_duration=600)
        self.iter = None
        self.cmd_queue = []  # heap queue

        # reset time
        for _, flight in self.flights.items():
            flight['date_time'] -= flight['date_time'].min() - flight['date_time'].iloc[0].normalize()

    def get_flight(self, n):
        def iter_flight():
            while True:
                ac_ids = list(self.flights.keys())
                np.random.shuffle(ac_ids)
                for id in ac_ids:
                    yield id, self.flights[id]
        if self.iter is None:
            self.iter = iter(iter_flight())

        res = {}
        for _ in range(n):
            k, v = next(self.iter)
            res[k] = v

        return res

    def update(self):
        pos = 0
        while pos < len(self.cmd_queue) and self.cmd_queue[pos][0] < sim.simt:
            t, cmd = self.cmd_queue[pos]
            stack.stack(cmd)
            pos += 1
        self.cmd_queue = self.cmd_queue[pos:]

    def reset(self):
        self.cmd_queue = []
        self.iter = None

    def mcre(self, n):
        ''' Create n flights'''
        flights = self.get_flight(n)
        cmds = generate_scenario(flights)
        self.cmd_queue = sorted(self.cmd_queue + cmds)
        # for t, cmd in cmds:
        #     heapq.heappush(self.cmd_queue, (t+sim.simt, cmd))
