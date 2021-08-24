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
        'update_interval': 5,

        # The update function is called after traffic is updated.
        'update': my_log.update,
        'reset': my_log.reset,
    }

    stackfunctions = {
    }

    return config, stackfunctions


class CustomLog(core.Entity):
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
