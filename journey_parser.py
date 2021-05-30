import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from connections import TripSegment, Connection
from distribution import Distribution
from journey import Journey, add_segment_to_journey
from journey_pointer import JourneyPointer
from sorted_lists import SortedJourneyList


def follow_path(journey_so_far: Journey,
                previous_trips_taken: List,
                destination: int,
                journey_pointers: Dict[int, SortedJourneyList],
                trip_connections: Dict[str, List[Connection]],
                min_chance_of_success: float,
                min_connection_time: timedelta,
                max_recursion_depth: int) -> List[Journey]:
    """
    Given a Journey and a destination, recursively follows JourneyPointers to arrive to the destination.

    :param journey_so_far: the journey followed to arrive to the current stop
    :param previous_trips_taken: TODO
    :param destination: the stop where the traveller wants to go
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
    :param trip_connections: maps trip_ids to the connections in the trip that can be taken
    :param min_chance_of_success: the minimum probability of success this journey should have to be kept
    :param min_connection_time: TODO
    :param max_recursion_depth: TODO
    :return: the possible Journeys to get from the source to the destination in time
    """
    if journey_so_far.success_probability() < min_chance_of_success:
        return []

    starting_stop = journey_so_far.current_arrival_stop
    arrival_time_at_starting_stop = journey_so_far.current_arrival_time()

    # If the journey was too long, return
    if len(journey_so_far) > max_recursion_depth:
        return []

    # If you've arrived at the destination, return
    if journey_so_far.reached_destination:
        return [journey_so_far]

    paths_from_here = []
    possible_paths = journey_pointers.get(starting_stop, [])
    for p in possible_paths:
        # Compute the time you need to arrive at the stop to take this path
        latest_arrival_time = p.arrival_time

        # Check that you're at the input early enough to make it, and that you're not getting onto a trip you got off of
        if ((arrival_time_at_starting_stop is None or arrival_time_at_starting_stop <= latest_arrival_time) and
                (p.enter_connection is None or p.enter_connection.trip_id not in previous_trips_taken)):

            new_journey = journey_so_far

            # Whether you can just follow a path to the end
            walked_to_end = False

            # If you need to walk to a stop, walk to a stop
            if p.footpath is not None:
                new_journey = add_segment_to_journey(new_journey, p.footpath)

                # If you've walked to the end, set the flag to true
                if p.footpath.arr_stop == destination:
                    paths_from_here += [new_journey]
                    walked_to_end = True

            # If you didn't walk to the end, check if you can take alternative routes or how to continue your journey
            if not walked_to_end and p.enter_connection is not None:

                # Add the trip we are taking to the trips taken
                previous_trips_taken = previous_trips_taken + [p.enter_connection.trip_id]

                # Look at the connections found on the trip
                connections = trip_connections.get(p.enter_connection.trip_id)

                if connections is None:
                    raise ValueError(f'Missing value in trip_connections for trip {p.enter_connection.trip_id}')

                # Check if alternative routes are available by getting out before the exit connection
                found_entry_connection = False
                found_exit_connection = False
                for c in connections:
                    if c == p.exit_connection:
                        found_exit_connection = True

                    if found_entry_connection and not found_exit_connection:
                        c_possible_paths: List[JourneyPointer] = journey_pointers.get(c.arr_stop, [])
                        if len(c_possible_paths) > 1:
                            for alt_journey_pointer in c_possible_paths:
                                # Check that the alternative route takes another trip, as we don't want to get off and
                                # immediately get back on a trip (if the connections are None than this edge was
                                # discovered during initialization and it arrives at the destination)
                                alt_journey_on_another_line = (
                                        alt_journey_pointer.enter_connection is None or
                                        alt_journey_pointer.enter_connection.trip_id != c.trip_id
                                )

                                # Check that there is enough time to catch the alternative connection (walking to
                                # the alternative stop and connection time)
                                alt_journey_starts_with_walk = alt_journey_pointer.footpath is not None

                                time_to_alt_stop = min_connection_time
                                if alt_journey_starts_with_walk:
                                    time_to_alt_stop += alt_journey_pointer.footpath.walk_time

                                alt_journey_can_be_taken = (
                                    alt_journey_pointer.enter_connection is None or
                                    alt_journey_pointer.enter_connection.dep_time >= c.arr_time + time_to_alt_stop
                                )

                                if alt_journey_on_another_line and alt_journey_can_be_taken:

                                    # Get out of the trip at c
                                    alt_trip_segment = TripSegment(p.enter_connection, c)
                                    alt_journey = add_segment_to_journey(
                                        new_journey, alt_trip_segment
                                    )
                                    # Walk if you need to
                                    if alt_journey_starts_with_walk:
                                        alt_journey = add_segment_to_journey(
                                            alt_journey, alt_journey_pointer.footpath
                                        )

                                    alt_previous_trips_taken = previous_trips_taken
                                    # take a train if you need to
                                    if alt_journey_pointer.enter_connection is not None:
                                        # TODO: this forces us to follow the alternative journey to the end ->
                                        # TODO: faster to compute but will remove possibilities
                                        alt_train_segment = TripSegment(
                                            alt_journey_pointer.enter_connection,
                                            alt_journey_pointer.exit_connection
                                        )

                                        alt_journey = add_segment_to_journey(
                                            alt_journey, alt_train_segment
                                        )

                                        alt_previous_trips_taken = previous_trips_taken + [alt_train_segment.trip_id]

                                    # Take the alternative route
                                    next_stop_ends = follow_path(
                                        alt_journey,
                                        alt_previous_trips_taken,
                                        destination,
                                        journey_pointers,
                                        trip_connections,
                                        min_chance_of_success,
                                        min_connection_time,
                                        max_recursion_depth
                                    )
                                    paths_from_here += next_stop_ends

                    if c == p.enter_connection:
                        found_entry_connection = True

                # Take the normal connection to the next stop
                trip_segment = TripSegment(p.enter_connection, p.exit_connection)
                new_journey = add_segment_to_journey(
                    new_journey, trip_segment
                )
                # Follow the path from the next stop
                next_stop_ends = follow_path(
                    new_journey,
                    previous_trips_taken,
                    destination,
                    journey_pointers,
                    trip_connections,
                    min_chance_of_success,
                    min_connection_time,
                    max_recursion_depth
                )
                paths_from_here += next_stop_ends
    return paths_from_here


def sort_journeys(journeys: List[Journey]) -> List[Journey]:
    """
    Sorts journeys based on the following criteria:
        1. Latest departure time
        2. Shortest walking time
        2. Fewest number of connections

    :param journeys: the journeys to sort
    :return: the sorted journeys
    """
    return sorted(journeys, key=lambda j: (j.departure_time(), -len(j)), reverse=True)


def find_resulting_paths(source: int,
                         destination: int,
                         src_coord: Tuple[float, float],
                         dst_coord: Tuple[float, float],
                         target_arrival: datetime,
                         min_connection_time: int,
                         journey_pointers: Dict[int, SortedJourneyList],
                         trip_connections: Dict[str, List[Connection]],
                         delay_distributions: Dict[int, Distribution],
                         min_chance_of_success: float,
                         max_recursion_depth: int) -> List[Journey]:
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
    :param max_recursion_depth: TODO
    :return: the possible Journeys to get from the source to the destination in time
    """
    coords = src_coord[0], src_coord[1], dst_coord[0], dst_coord[1]
    min_co_time = timedelta(minutes=math.ceil(min_connection_time))
    start_journey = Journey(
        source,
        destination,
        coords,
        [],
        target_arrival,
        min_co_time,
        delay_distributions,
        arrival_time_at_last_stop=None,
        success_probability=1.0,
    )
    return sort_journeys(follow_path(
        start_journey,
        [],
        destination,
        journey_pointers,
        trip_connections,
        min_chance_of_success,
        min_co_time,
        max_recursion_depth,
    ))
