from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from connections import TripSegment, Connection
from journey import Journey
from journey_pointer import JourneyPointer
from sorted_lists import SortedJourneyList


def follow_path(journey_to_input: Journey,
                destination: int,
                journey_pointers: Dict[int, SortedJourneyList],
                trip_connections: Dict[str, List[Connection]],
                main_trip_id: Optional[Any] = None) -> List[Journey]:
    """
    Given a Journey and a destination, recursively follows JourneyPointers to arrive to the destination.

    :param journey_to_input: the journey followed to arrive to the current stop
    :param destination: the stop where the traveller wants to go
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
    :param trip_connections: maps trip ids to the connections in the trip that can be taken
    :param main_trip_id: the id of a trip that can't be taken from this stop (as we are at an alternative path)
    :return: the possible Journeys to get from the source to the destination in time
    """
    input_stop = journey_to_input.destination()
    time_at_input = journey_to_input.arrival_time()

    if len(journey_to_input) > 8:
        return []
    if input_stop == destination:
        return [journey_to_input]

    paths_from_here = []
    possible_paths = journey_pointers.get(input_stop, [])
    for p in possible_paths:
        # Compute the time you need to arrive at the stop to take this path
        latest_arrival_time = p.arrival_time

        # Check that you're at the input early enough to make it
        if time_at_input is None or time_at_input <= latest_arrival_time:

            new_journey_to_input = Journey(
                journey_to_input.source(),
                journey_to_input.coord,
                journey_to_input.paths.copy(),
                journey_to_input.target_arrival_time(),
                journey_to_input.min_co_time
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

            # If you didn't walk to the end and you're not in an alternative route looking at the main trip you just
            # left, continue looking
            if not walked_to_end and p.enter_connection.trip_id != main_trip_id:
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
                                    next_stop_ends = follow_path(alternative_journey, destination, journey_pointers,
                                                                 trip_connections, main_trip_id=c.trip_id)
                                    paths_from_here += next_stop_ends
                # Take the normal connection to the next stop
                trip_segment = TripSegment(p.enter_connection, p.exit_connection)
                new_journey_to_input.add_segment(trip_segment)

                if trip_segment.exit_connection.arr_stop == destination:
                    paths_from_here += [new_journey_to_input]
                    break

                # Follow the path from the next stop
                next_stop_ends = follow_path(new_journey_to_input, destination, journey_pointers, trip_connections)
                paths_from_here += next_stop_ends
    return paths_from_here


def find_resulting_paths(source: int,
                         destination: int,
                         src_coord: Tuple[float, float],
                         dst_coord: Tuple[float, float],
                         target_arrival: datetime,
                         min_connection_time,
                         journey_pointers: Dict[int, SortedJourneyList],
                         trip_connections: Dict[str, List[Connection]]) -> List[Journey]:
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
    :return: the possible Journeys to get from the source to the destination in time
    """
    coords = src_coord[0], dst_coord[1], src_coord[0], dst_coord[1]
    start_journey = Journey(source, coords, [], target_arrival, min_connection_time)
    return follow_path(start_journey, destination, journey_pointers, trip_connections)
