import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from connection_scan import connection_scan
from distribution import Distribution


# Helpers
################################################################################################################


def time(minutes):
    return datetime(year=2021, month=5, day=28, hour=12, minute=00) + timedelta(minutes=minutes)


# Generate Distributions
################################################################################################################


def generate_integer_gaussian(mean_range=(0.75, 1.75), sigma_range=(1.5, 2.5), num_values=1000, max_delay=20):
    mean = random.uniform(*mean_range)
    sigma = random.uniform(*sigma_range)
    values = max_delay * [0]
    for _ in range(num_values):
        v = random.gauss(mean, sigma)
        if v > 0:
            values[int(v)] += 1
    return values


def probabilities(int_gaussian):
    num_values = sum(int_gaussian)
    return [v / num_values for v in int_gaussian]


list_distributions = []

for i in range(2):
    time_delays = list(range(20))
    p = probabilities(generate_integer_gaussian())
    distribution = Distribution(time_delays, p, i)
    list_distributions.append([i, distribution])

delay_distributions = {i: d for i, d in list_distributions}


# Generate Data
################################################################################################################


# (ttype, dep_stop, arr_stop, dep_time, arr_time, trip, distribution_id)
e_c = [
    ['bus', 1, 3, time(15), time(18), '||', 0],
    ['train', 1, 2, time(13), time(15), '| ', 1],
    ['bus', 0, 1, time(10), time(15), '||', 0],
    ['train', 4, 1, time(9), time(13), '| ', 1],
    ['bus', 6, 0, time(8), time(10), '||', 0],
    ['train', 5, 4, time(7), time(12), '| ', 1],
]

df_connections = pd.DataFrame(
    e_c, columns=['route_desc', 'src_id', 'dst_id', 'departure_time_dt',
                  'arrival_time_dt', 'trip_id', 'distribution_id']
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
min_change_of_success = 0.5
journeys_per_stop = 2

results = connection_scan(df_connections, footpaths, delay_distributions, source, destination, target_arrival,
                          time_per_connection, paths_to_find, min_change_of_success, journeys_per_stop)

print('Results')
for i, r in enumerate(results):
    print(f'Itinerary {i}: {r.duration()} minutes, '
          f'{100 * r.success_probability(delay_distributions):.1f}% chance of success')
    print(f'  {r}')
    print()

print('Change times:')
for i, r in enumerate(results):
    print(f'Itinerary {i}:')
    for trip_seg, change_time in r.changes():
        print(f'  {trip_seg}: {change_time}min')
    print()
