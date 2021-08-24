import pandas as pd
import numpy as np

from pathlib import Path
from typing import Any, Dict, Union

acids = {}
default_ac_mdl = "B738"


def split_flight(
        all_df: pd.DataFrame,
        split_threshold=pd.Timedelta(seconds=600),
        min_points=100,
        min_duration=pd.Timedelta(seconds=600),
):
    if type(split_threshold) == int:
        split_threshold = pd.Timedelta(seconds=split_threshold)
    if type(min_duration) == int:
        min_duration = pd.Timedelta(seconds=min_duration)

    def split_flight_same_callsign(name: str, traj: pd.DataFrame):
        # traj.sort_values('posix_time', inplace=True)
        idx = traj['date_time'].diff() > split_threshold
        result = []
        pre_pos = 0
        # traj['posix_time'] = (traj['posix_time'] - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')
        # traj['posix_velo_time'] = (traj['posix_velo_time'] - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')
        split_points = list(idx[idx == True].index.values)
        split_points.append(traj.shape[0])
        for i in split_points:
            if i - pre_pos > min_points and \
                    (traj['date_time'].iloc[i-1] - traj['date_time'].iloc[pre_pos]) >= min_duration:
                result.append(((name, len(result)), traj.iloc[pre_pos:i].reset_index(drop=True)))
            pre_pos = i
        return result

    flight_trajectories = all_df.groupby('callsign', sort=False)
    results = {
        k: v for name, tr in flight_trajectories for k, v in
        split_flight_same_callsign(name, tr.sort_values(by='posix_time', ignore_index=True))
    }
    return results


def generate_scenario(all_flights: Dict[Any, pd.DataFrame], delta_time=10, min_points=100):
    result = []
    min_duration = pd.Timedelta(seconds=delta_time)

    for key, traj in all_flights.items():
        traj = traj.dropna(
            subset=["callsign", "latitude", "longitude", "track_angle", "geo_altitude", "calibrated_speed"]
        )
        if traj.shape[0] < min_points:
            continue
        traj.loc[:, 'timestamp'] = (traj['date_time'] - traj['date_time'].iloc[0].normalize()) / pd.Timedelta(seconds=1)
        for i, row in enumerate(traj.itertuples()):
            if i == 0:
                pre_time = row.date_time
                cmdstr = f'CRE {row.callsign}, {default_ac_mdl}, {row.latitude:.7f}, {row.longitude:.7f}, ' \
                         f'{row.track_angle:.2f}, {row.geo_altitude:.4f}, {row.calibrated_speed:.4f}'
                result.append((row.timestamp, cmdstr))

                if row.geo_vertical_rate:
                    result.append((row.timestamp, f"VS {row.callsign}, {row.geo_vertical_rate}"))

            elif i == traj.shape[0] - 1:
                result.append((row.timestamp, f'DELAY 5 DEL {row.callsign}'))
            else:
                if row.date_time - pre_time < min_duration:
                    vspd = row.geo_vertical_rate if row.geo_vertical_rate else 0

                    cmdstr = f'MOVE {row.callsign}, {row.latitude:.7f}, {row.longitude:.7f}, {row.geo_altitude:.4f}, ' \
                             f'{row.track_angle:.2f}, {row.calibrated_speed:.4f}, {vspd:.4f}'

                    result.append((row.timestamp, cmdstr))
                    pre_time = row.date_time

    result.sort()
    return result


def write_scenario_to_file(cmds: Dict[float, str], file_name: Union[Path, str],
                           template: Union[Path, str] = None) -> None:
    preset = []
    if template:
        with open(template, 'rt') as fp:
            preset += fp.readlines()
    with open(file_name, 'wt') as fp:
        fp.writelines(preset)
        fp.write("\n")
        for row in cmds:
            time_str = f"{int(row[0] // 3600)}:{int(row[0] // 60)}:{row[0] % 60:.2f}"
            fp.write(f"{time_str}>{row[1]}\n")


def read_space_based_adsb(file_path: Union[Path, str], nrows=None, reset_datetime=True):
    raw_data = pd.read_csv(file_path, nrows=nrows)

    columns_mapping = {
        'Date': 'Date',
        'I073__time_reception_position__val': 'position_reception_time',
        'I075__time_reception_velocity__val': 'velocity_reception_time',
        'I080__TAddr__val': 'identifier',
        'I131__Lat__val': 'latitude',
        'I131__Lon__val': 'longitude',
        'I140__geometric_height__val': 'geo_altitude',
        'I145__FL__val': 'flight_level',
        'I146__Alt__val': 'altitude',
        'I151__TAS__val': 'true_airspeed',
        # 'I152__MHdg__val': '',
        'I157__GVR__val': 'geo_vertical_rate',
        'I160__GS__val': 'ground_speed',
        'I160__TA__val': 'track_angle',
        'I170__TId__val': 'callsign',
        # 'I200__ICF__val': '',
    }

    used_columns = [
        'Date', 'position_reception_time', 'velocity_reception_time',
        'identifier', 'latitude', 'longitude', 'geo_altitude', 'flight_level',
        'ground_speed', 'track_angle', 'callsign',
        'date_time', 'posix_velo_time', 'posix_time', 'calibrated_speed', 'geo_vertical_rate'
    ]

    raw_data.rename(columns=columns_mapping, inplace=True)

    # map timestamp to posix time
    raw_data['date_time'] = pd.to_datetime(raw_data['Date']) + \
                            pd.to_timedelta(raw_data['position_reception_time'], unit='s')
    raw_data['posix_velo_time'] = pd.to_datetime(raw_data['Date']) + \
                                  pd.to_timedelta(raw_data['velocity_reception_time'], unit='s')

    raw_data.loc[:, 'posix_time'] = (raw_data['date_time'] - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')
    raw_data.loc[:, 'posix_velo_time'] = (raw_data['posix_velo_time'] - pd.Timestamp("1970-01-01")) / pd.Timedelta('1s')

    raw_data['callsign'] = raw_data['callsign'].str.strip()
    raw_data['calibrated_speed'] = raw_data['ground_speed'] * 3600
    processed_data = raw_data[used_columns]

    if reset_datetime:
        min_date_time = processed_data['date_time'].min()
        processed_data.loc[:, 'date_time'] -= min_date_time - min_date_time.normalize()
    return processed_data


def flight_auto_timeshift(flights: Dict[Any, pd.DataFrame], seed=None) -> Dict[Any, pd.DataFrame]:
    np.random.seed(seed)

    ac_ids = list(flights.keys())
    np.random.shuffle(ac_ids)

    result = {}

    for ac_id in ac_ids:
        trajectory = flights[ac_id].copy()
        coeff = np.random.uniform(low=0.3)
        trajectory['date_time'] -= coeff * (trajectory['date_time'] - trajectory['date_time'].iloc[0])
        result[ac_id] = trajectory

    return result


if __name__ == "__main__":
    file_path = Path('/home/viethoangcr/Documents/Dataset/Dataset/ADSB_SPACE_BASED_TRACKS_2020_02.csv.gz')

    proccessed_df = read_space_based_adsb(file_path, nrows=250000)

    flights = split_flight(proccessed_df, min_points=20, min_duration=60)
    new_randomized_flights = flight_auto_timeshift(flights, seed=7)

    # merge flights and generate scenario file

    cmds = generate_scenario(flights)
    write_scenario_to_file(
        cmds, "/home/viethoangcr/Documents/Workspace/bluesky/scenario/ATMRI/demo_adsb.scn",
        template="/home/viethoangcr/Documents/Workspace/bluesky/scenario/ATMRI/fir.scn",
    )

    cmds = generate_scenario(new_randomized_flights)

    write_scenario_to_file(
        cmds, "/home/viethoangcr/Documents/Workspace/bluesky/scenario/ATMRI/demo_rand_adsb.scn",
        template="/home/viethoangcr/Documents/Workspace/bluesky/scenario/ATMRI/fir.scn",
    )
