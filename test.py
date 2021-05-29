from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from connection_scan import connection_scan


def time(minutes):
    return datetime(year=2021, month=5, day=28, hour=12, minute=00) + timedelta(minutes=minutes)


# (ttype, dep_stop, arr_stop, dep_time, arr_time, trip)
e_c = [
    ['bus', 1, 3, time(15), time(18), '||'],
    ['train', 1, 2, time(13), time(15), '| '],
    ['bus', 0, 1, time(10), time(15), '||'],
    ['train', 4, 1, time(9), time(13), '| '],
    ['bus', 6, 0, time(8), time(10), '||'],
    ['train', 5, 4, time(7), time(12), '| '],
]

df_connections = pd.DataFrame(
    e_c, columns=['route_desc', 'src_id', 'dst_id', 'departure_time_dt', 'arrival_time_dt', 'trip_id']
)

footpaths = csr_matrix(np.array([
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 2, 0, 0, 0],
    [0, 0, 2, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 2],
    [0, 0, 0, 0, 0, 2, 0],
]))

source = 5
destination = 3

target_arrival = time(20)
time_per_connection = 1.0
paths_to_find = 5
journeys_per_stop = 2

results = connection_scan(df_connections, footpaths, source, destination, target_arrival,
                          time_per_connection, paths_to_find, journeys_per_stop)

print('Results')
for r in results:
    print(r)
