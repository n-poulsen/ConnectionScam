from typing import Dict, List
from datetime import datetime, timedelta
import math

import pandas as pd
from scipy.sparse import csr_matrix

from connections import Connection, Footpath
from journey_pointer import JourneyPointer
from journey_parser import find_resulting_paths
from sorted_lists import SortedJourneyList


def min_to_timedelta(minutes: float):
    return timedelta(minutes=math.ceil(minutes))


def connection_scan(df_connections: pd.DataFrame,
                    footpaths: csr_matrix,
                    source: int,
                    destination: int,
                    target_arrival: datetime,
                    time_per_connection: float,
                    paths_to_find: int,
                    journeys_per_stop: int = 2,
                    min_times_to_find_source: int = 3):
    """
    Custom Connection Scan Algorithm
    """
    source_found_n_times = 0

    journey_pointers: Dict[int, SortedJourneyList] = {}
    trip_taken: Dict[str, Connection] = {}

    # A dictionary mapping trip ids to a list of connections in the trip that were found and can be taken
    trip_connections: Dict[str, List[Connection]] = {}

    # Set the latest arrival time at the destination to the target time
    journey_pointers[destination] = SortedJourneyList([JourneyPointer(target_arrival, None, None, None)])

    # For all stops that we can walk to from the destination, update the latest possible arrival time
    destination_footpaths = footpaths.getrow(destination)
    for train_stop, walking_time_float in zip(destination_footpaths.indices, destination_footpaths.data):

        # Ceil the walking time to minutes, create timedelta object
        walk_time = min_to_timedelta(walking_time_float)
        path = Footpath(train_stop, destination, walk_time)

        # Latest arrival time is time you must be
        latest_arrival = target_arrival - walk_time

        # Add the journey pointer to the latest arrival times for the train stop
        journey_pointers[train_stop] = SortedJourneyList([JourneyPointer(latest_arrival, None, None, path)])

    # Iterate over connections in the network
    for idx, row in df_connections.iterrows():
        # trip_id: str, src_id: int (long), dst_id: int (long), departure_time_dt: datetime, arrival_time_dt: datetime
        c = Connection(row.trip_id, row.route_desc, row.src_id, row.dst_id, row.departure_time_dt, row.arrival_time_dt)

        # Update the connections that can be taken in the trip
        c_trip_connections = trip_connections.get(c.trip_id)
        if c_trip_connections is None:
            c_trip_connections = [c]
        else:
            c_trip_connections = [c] + c_trip_connections
        trip_connections[c.trip_id] = c_trip_connections

        trip_can_be_taken = trip_taken.get(c.trip_id)
        arr_stop_req_arrival_times = journey_pointers.get(c.arr_stop, SortedJourneyList([]))

        # A connection can be taken if:
        #   * the connection's trip can be taken
        #   * the connection gets you to the next stop before its latest arrival time, which is the case if
        #     * there is no required arrival time for the destination stop (-infinity)
        #     * the required arrival time for the destination stop is earlier than the arrival of the train
        if (trip_can_be_taken is not None or (
                len(arr_stop_req_arrival_times) > 0 and
                arr_stop_req_arrival_times[0].arrival_time >= c.arr_time)):

            if trip_can_be_taken is None:
                trip_taken[c.trip_id] = c

            # Update the latest arrival time for c.dep_stop, as arriving at c.dep_stop allows you to arrive to
            # c.arr_stop before you need to be there
            dep_stop_req_arrival_times = journey_pointers.get(c.dep_stop)
            if dep_stop_req_arrival_times is None:
                dep_stop_req_arrival_times = SortedJourneyList([])
                journey_pointers[c.dep_stop] = dep_stop_req_arrival_times

            dep_stop_latest_arr_time = c.dep_time - min_to_timedelta(time_per_connection)
            dep_stop_req_arrival_times.append(
                JourneyPointer(dep_stop_latest_arr_time, c, trip_taken[c.trip_id], None)
            )

            if len(dep_stop_req_arrival_times) > journeys_per_stop:
                dep_stop_req_arrival_times.remove_earliest_arrival()

            if c.dep_stop == source:
                source_found_n_times += 1
                if source_found_n_times >= min_times_to_find_source:
                    paths_found = find_resulting_paths(
                        source, destination, target_arrival, time_per_connection, journey_pointers, trip_connections
                    )
                    if len(paths_found) >= paths_to_find:
                        return paths_found

            # Iterate over stops we can walk to from the departure, as arriving there and walking to c.dep_stop can get
            # you to the destination
            neighbor_stops = footpaths.getrow(c.dep_stop)
            for train_stop, walking_time_float in zip(neighbor_stops.indices, neighbor_stops.data):

                neighbor_req_arrival_times = journey_pointers.get(train_stop)
                if neighbor_req_arrival_times is None:
                    neighbor_req_arrival_times = SortedJourneyList([])
                    journey_pointers[train_stop] = neighbor_req_arrival_times

                walk_time = min_to_timedelta(walking_time_float + time_per_connection)
                path = Footpath(train_stop, c.dep_stop, walk_time)
                latest_arrival = c.dep_time - walk_time

                neighbor_req_arrival_times.append(
                    JourneyPointer(latest_arrival, c, trip_taken[c.trip_id], path)
                )

                if len(neighbor_req_arrival_times) > journeys_per_stop:
                    neighbor_req_arrival_times.remove_earliest_arrival()

                if train_stop == source:
                    source_found_n_times += 1
                    if source_found_n_times >= min_times_to_find_source:
                        paths_found = find_resulting_paths(
                            source, destination, target_arrival, time_per_connection, journey_pointers, trip_connections
                        )
                        if len(paths_found) >= paths_to_find:
                            return paths_found

    paths_found = find_resulting_paths(
        source, destination, target_arrival, time_per_connection, journey_pointers, trip_connections
    )
    return paths_found
