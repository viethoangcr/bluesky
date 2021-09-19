''' This plugin provide wrapper for . '''
import numpy as np
from bluesky import stack, sim, traffic
from bluesky.tools import geo
from bluesky.tools.aero import nm
from bluesky.traffic.asas import ConflictDetection

model = None


### Initialization function of the adsbfeed plugin.
def init_plugin():
    # Initialize Modesbeast reader
    global model
    model = TrajectoryPredictionWrapper()

    # Configuration parameters
    config = {
        'plugin_name':     'TP_EVALUATION',
        'plugin_type':     'sim',
        'update_interval': 0.0,
        'update':       model.update
        }


    return config


class TrajectoryPredictionWrapper(object):
    def __init__(self):
        self.acids = dict()
        pass

    def update(self):

        pass

    def interpolate(self):

        pass

    def predict(self):
        pass

    def evaluate(self):
        pass