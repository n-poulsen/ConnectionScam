from typing import Dict, List
from datetime import datetime, timedelta
import math

import pandas as pd
from scipy.sparse import csr_matrix

from connections import Connection, Footpath
from distribution import Distribution
from journey_pointer import JourneyPointer
from journey_parser import find_resulting_paths
from sorted_lists import SortedJourneyList


def min_to_timedelta(minutes: float) -> timedelta:
    """
    Creates a timedelta object from a ceiled number of minutes.

    :param minutes: the number of minutes to ceil and transform to a timedelta object
    :return: the number of minutes, ceiled to the nearest integer
    """
    return timedelta(minutes=math.ceil(minutes))


def connection_scan(df_connections: pd.DataFrame,
                    footpaths: csr_matrix,
                    delay_distributions: Dict[int, Distribution],
                    source: int,
                    destination: int,
                    target_arrival: datetime,
                    time_per_connection: int,
                    journeys_to_find: int,
                    min_chance_of_success: float,
                    journeys_per_stop: int = 2,
                    min_times_to_find_source: int = 3,
                    max_recursion: int = 8):
    """
    Custom Connection Scan Algorithm, which operates in reverse order.

    :param df_connections: Each row represents a connection (an edge in the graph). The rows are sorted in descending
        order with respect to the departure times of the connections. It should contain no edges for which the arrival
        time is later than the user's target arrival time. Should contain the columns:
            * 'src_id': int. the index of the departure stop
            * 'dst_id': int. the index of the arrival stop
            * 'departure_time_dt': datetime.datetime. the scheduled departure time
            * 'arrival_time_dt': datetime.datetime. the scheduled arrival time
            * 'trip_id': Any. the ID of the trip to which this connection belongs
            * 'route_desc': str. the mode of transport of the trip (e.g., 'bus', 'train', ...)
            * 'distribution_id': int. The id of the distribution of delays for this distribution
    :param footpaths: A sparse matrix containing the footpaths in the map. Row i contains the stops reachable from stop
        i by foot. There should be no self-loops (i <-> i).
    :param delay_distributions: maps distribution delay groups to their distributions
    :param source: The index of the stop from which the user wants to depart.
    :param destination: The index of the stop where the user wants to go.
    :param target_arrival: The time at which the user wants to arrive to their target destination.
    :param time_per_connection: The amount of time (in minutes) it takes for the user to change transportation vehicles
        at a stop (i.e., the amount of time it takes to change tracks at a train station).
    :param journeys_to_find: The minimum number of possible Journeys to find (if possible, as if there are not enough edges
        in the DataFrame, fewer journeys will be returned)
    :param min_chance_of_success: the minimum probability of success a journey should have to be kept
    :param journeys_per_stop: The maximum number of JourneyPointers to store at each stop.
    :param min_times_to_find_source: The minimum number of times the source must be found before returning the Journeys
        (if possible, as if there are not enough edges in the DataFrame, it will be found fewer times).
    :param max_recursion: the maximum number of segments that can be in a journey
    :return: A list containing all Journeys found.
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
        route_desc = row.get('route_desc', 'unknown')
        dep_time = row.get('departure_time_dt')
        arr_time = row.get('arrival_time_dt')
        distribution_id = row.get('distribution_id', 0)
        c = Connection(row.trip_id, route_desc, row.src_id, row.dst_id, dep_time, arr_time, distribution_id)

        # Update the connections that can be taken in the trip
        c_trip_connections = trip_connections.get(c.trip_id)
        if c_trip_connections is None:
            c_trip_connections = [c]
        else:
            c_trip_connections = [c] + c_trip_connections
        trip_connections[c.trip_id] = c_trip_connections

        trip_can_be_taken = trip_taken.get(c.trip_id)
        arr_stop_req_arrival_times = journey_pointers.get(c.arr_stop, SortedJourneyList([]))

        # A connection can be taken if either:
        #   * the connection's trip can be taken
        #   * the connection gets you to the next stop before its latest arrival time (i.e. the arrival time of the
        #     connection is earlier than the time at which you need to arrive). If there is no required arrival time, it
        #     is assumed to be -infinity, and hence a user cannot get there in time.
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

            # If the source was found and it is the required number of times, try to generate the journeys
            if c.dep_stop == source:
                source_found_n_times += 1
                if source_found_n_times >= min_times_to_find_source:
                    paths_found = find_resulting_paths(
                        source, destination, target_arrival, time_per_connection, journey_pointers, trip_connections,
                        delay_distributions, min_chance_of_success, max_recursion
                    )
                    if len(paths_found) >= journeys_to_find:
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
                            source, destination, target_arrival, time_per_connection, journey_pointers,
                            trip_connections, delay_distributions, min_chance_of_success, max_recursion
                        )
                        if len(paths_found) >= journeys_to_find:
                            return paths_found

    # If the source was not found the required number of times, still try to find paths.
    paths_found = find_resulting_paths(
        source, destination, target_arrival, time_per_connection, journey_pointers, trip_connections,
        delay_distributions, min_chance_of_success, max_recursion
    )
    return paths_found
