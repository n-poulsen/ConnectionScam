from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from connections import TripSegment, Connection
from distribution import Distribution
from journey import Journey
from journey_pointer import JourneyPointer
from sorted_lists import SortedJourneyList


def follow_path(journey_so_far: Journey,
                destination: int,
                journey_pointers: Dict[int, SortedJourneyList],
                trip_connections: Dict[str, List[Connection]],
                delay_distributions: Dict[int, Distribution],
                min_chance_of_success: float) -> List[Journey]:
    """
    Given a Journey and a destination, recursively follows JourneyPointers to arrive to the destination.

    :param journey_so_far: the journey followed to arrive to the current stop
    :param destination: the stop where the traveller wants to go
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
    :param trip_connections: maps trip_ids to the connections in the trip that can be taken
    :param delay_distributions: maps distribution delay groups to their distributions
    :param min_chance_of_success: the minimum probability of success this journey should have to be kept
    :return: the possible Journeys to get from the source to the destination in time
    """
    if journey_so_far.success_probability(delay_distributions) < min_chance_of_success:
        return []

    starting_stop = journey_so_far.destination()
    arrival_time_at_starting_stop = journey_so_far.arrival_time()

    # If the journey was too long, return
    if len(journey_so_far) > 8:
        return []

    # If you've arrived at the destination, return
    if starting_stop == destination:
        return [journey_so_far]

    previous_trips_taken = [
        trip_segment.trip_id
        for trip_segment in journey_so_far.paths
        if isinstance(trip_segment, TripSegment)
    ]

    paths_from_here = []
    possible_paths = journey_pointers.get(starting_stop, [])
    for p in possible_paths:
        # Compute the time you need to arrive at the stop to take this path
        latest_arrival_time = p.arrival_time

        # Check that you're at the input early enough to make it, and that you're not getting onto a trip you got off of
        if ((arrival_time_at_starting_stop is None or arrival_time_at_starting_stop <= latest_arrival_time) and
                (p.enter_connection is None or p.enter_connection.trip_id not in previous_trips_taken)):

            new_journey_to_input = Journey(
                journey_so_far.source(),
                journey_so_far.coord,
                journey_so_far.paths.copy(),
                journey_so_far.target_arrival_time(),
                journey_so_far.min_co_time
            )

            # Whether you can just follow a path to the end
            walked_to_end = False

            # If you need to walk to a stop, walk to a stop
            if p.footpath is not None:
                new_journey_to_input.add_segment(p.footpath)

                # If you've walked to the end, set the flag to true
                if p.footpath.arr_stop == destination:
                    paths_from_here += [new_journey_to_input]
                    walked_to_end = True

            # If you didn't walk to the end, check if you can take alternative routes or how to continue your journey
            if not walked_to_end and p.enter_connection is not None:
                connections = trip_connections.get(p.enter_connection.trip_id)

                if connections is None:
                    raise ValueError(f'Missing value in trip_connections for trip {p.enter_connection.trip_id}')

                # Check if alternative routes are available by getting out before the exit connection
                found_entry_connection = False
                found_exit_connection = False
                for c in connections:
                    if c == p.enter_connection:
                        found_entry_connection = True

                    if c == p.exit_connection:
                        found_exit_connection = True

                    if found_entry_connection and not found_exit_connection:
                        c_possible_paths: List[JourneyPointer] = journey_pointers.get(c.arr_stop, [])
                        if len(c_possible_paths) > 1:
                            for alternative_journey_pointer in c_possible_paths:

                                # Check that the alternative exit is not continuing on the same trip and that it can be
                                # taken as the latest arrival time is not too early (or is simply a footpath)
                                if (alternative_journey_pointer.enter_connection is None or
                                        (alternative_journey_pointer.enter_connection.trip_id != c.trip_id and
                                         alternative_journey_pointer.enter_connection.dep_time > c.arr_time)):
                                    # Create the alternative route
                                    alternative_journey = Journey(
                                        new_journey_to_input.source(),
                                        new_journey_to_input.coord,
                                        new_journey_to_input.paths.copy(),
                                        new_journey_to_input.target_arrival_time(),
                                        new_journey_to_input.min_co_time
                                    )
                                    # Get out of the trip at c
                                    alternative_trip_segment = TripSegment(p.enter_connection, c)
                                    alternative_journey.add_segment(alternative_trip_segment)
                                    # Take the alternative route
                                    next_stop_ends = follow_path(
                                        alternative_journey, destination, journey_pointers, trip_connections,
                                        delay_distributions, min_chance_of_success
                                    )
                                    paths_from_here += next_stop_ends
                # Take the normal connection to the next stop
                trip_segment = TripSegment(p.enter_connection, p.exit_connection)
                new_journey_to_input.add_segment(trip_segment)
                # Follow the path from the next stop
                next_stop_ends = follow_path(
                    new_journey_to_input, destination, journey_pointers, trip_connections, delay_distributions,
                    min_chance_of_success
                )
                paths_from_here += next_stop_ends
    return paths_from_here


def sort_journeys(journeys: List[Journey]) -> List[Journey]:
    """
    Sorts journeys based on the following criteria:
        1. Lastest departure time first
        2. Fewest number of connections first

    :param journeys: the journeys to sort
    :return: the sorted journeys
    """
    return sorted(journeys, key=lambda j: (j.departure_time(), -len(j)), reverse=True)


def find_resulting_paths(source: int,
                         destination: int,
                         src_coord: Tuple[float, float],
                         dst_coord: Tuple[float, float],
                         target_arrival: datetime,
                         min_connection_time,
                         journey_pointers: Dict[int, SortedJourneyList],
                         trip_connections: Dict[str, List[Connection]],
                         delay_distributions: Dict[int, Distribution],
                         min_chance_of_success: float) -> List[Journey]:
    """
    Recursively travels through the journey pointers to find paths between the source and the destination.

    :param source: the stop from which the traveller starts
    :param destination: the stop where the traveller wants to go
    :param src_coord: the coordinates of the stop where the traveller starts
    :param dst_coord: the coordinates of the stop where the traveller wants to go
    :param target_arrival: the time at which the traveller needs to get there
    :param min_connection_time: the minimum amount of time needed to change trains
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
    :param trip_connections: maps trip ids to the connections in the trip that can be taken
    :param delay_distributions: maps distribution delay groups to their distributions
    :param min_chance_of_success: the minimum probability of success a journey should have to be kept
    :return: the possible Journeys to get from the source to the destination in time
    """
    coords = src_coord[0], dst_coord[1], src_coord[0], dst_coord[1]
    start_journey = Journey(source, coords, [], target_arrival, min_connection_time)
    return sort_journeys(follow_path(
        start_journey, destination, journey_pointers, trip_connections, delay_distributions, min_chance_of_success
    ))
