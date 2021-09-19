"""
Airspace Design Contest Scenario Generator:

Draw circles and runways in use
Generate traffic at edges and at airports
Make sure scenario can be saved

"""

from bluesky import core, stack, traf, sim, tools, navdb  # , settings, navdb, traf, sim, scr, tools
from bluesky.tools import datalog
from bluesky.tools.position import txt2pos
from bluesky.tools.geo import kwikpos
# from bluesky.tools import areafilter
# from bluesky.tools.aero import vtas2cas,ft
# from bluesky.tools.misc import degto180

import csv
import sys
import time

my_log = None


def init_plugin():
    print("Initialising logging plugin")
    global my_log
    my_log = CustomLog()

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name': 'CUSTOMLOG',
        'plugin_type': 'sim',
        'update_interval': .1,

        # The update function is called after traffic is updated.
        'update': my_log.update,
        'reset': my_log.reset,
    }

    stackfunctions = {
    }

    return config, stackfunctions


class CustomLog(core.Entity):
    ''' Example new entity object for BlueSky. '''

    def __init__(self, time_step=15):
        super().__init__()
        self.ac_ids = {}
        self.time_step = time_step
        stack.stack('PAN WSSS')

        sim.ffmode = True
        self.flush_time = sim.simt
        print(sys.argv)
        try:
            id = sys.argv.index("--log-output")
            self.output_file = sys.argv[id+1]
        except ValueError:
            self.output_file = f'output/custom_log_{int(time.time())}.csv'

        self.buffer = []
        self.buffer.append(('sim_time', 'acid', 'lat', 'lon', 'alt'))
        self.flush_to_file(force=True)

    def flush_to_file(self, force=False):
        if force or (sim.simt - self.flush_time >= 10*60):
            print(f"Writing AC position to file {self.output_file} at sim time {sim.simt}")
            with open(self.output_file, 'at') as csv_file:
                csvwriter = csv.writer(csv_file, delimiter=',')
                for line in self.buffer:
                    csvwriter.writerow(line)
            self.flush_time = int(sim.simt)
            self.buffer.clear()

    def update(self):
        ''' Print whatever we need to'''

        current_time = sim.simt
        sim.ffmode = True

        for ac_id, lat, lon, alt in zip(traf.id, traf.lat, traf.lon, traf.alt):
            if ac_id not in self.ac_ids or current_time - self.ac_ids[ac_id] >= self.time_step:
                self.buffer.append((current_time, ac_id, lat, lon, alt))
                self.ac_ids[ac_id] = int(current_time)
        self.flush_to_file()

    def reset(self):
        pass


class ConflictCustomLog(core.Entity):
    ''' Example new entity object for BlueSky. '''

    def __init__(self):
        super().__init__()
        self.prevconfpairs = set()
        self.confinside_all = 0
        self.conflog = datalog.crelog('CUSTOM_LOG', 5)
        self.conflog.start()

    def log(self, s: str):
        self.conflog.log(s)
        print(s)

    def update(self):
        ''' Print whatever we need to'''

        confpairs_new = list(set(traf.cd.confpairs) - self.prevconfpairs)
        if confpairs_new:
            self.conflog.log(confpairs_new)
            t = sim.simt
            self.log(f"Detect at timestamp {int(t // 3600)}:{int(t // 60)}:{t % 60:.2f}: "
                  f"{len(confpairs_new)} new conflict pairs")
            self.log(','.join([f"({pair[0]}, {pair[1]})" for pair in confpairs_new]))

        self.prevconfpairs = set(traf.cd.confpairs)

    def reset(self):
        self.prevconfpairs = set()
        self.conflog.reset()
        self.conflog.start()