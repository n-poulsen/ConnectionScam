from datetime import datetime
from typing import Dict, List

from connections import TripSegment
from journey import Journey
from sorted_lists import SortedJourneyList


def follow_path(journey_to_input: Journey, destination: int,
                journey_pointers: Dict[int, SortedJourneyList]) -> List[Journey]:
    """
    Given a journey and a destination, recursively follows journey pointers to arrive to the destination.

    :param journey_to_input: the journey followed to arrive to the current stop
    :param destination: the stop where the traveller wants to go
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
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
                journey_to_input.paths.copy(),
                journey_to_input.target_arrival_time()
            )

            # If you need to walk to a node, walk to a stop
            if p.footpath is not None:
                new_journey_to_input.add_segment(p.footpath)

                # If you've walked to the end, return
                if p.footpath.arr_stop == destination:
                    paths_from_here += [new_journey_to_input]
                    break

            # Take your connection to the next stop
            trip_segment = TripSegment(p.enter_connection, p.exit_connection)
            new_journey_to_input.add_segment(trip_segment)

            if trip_segment.exit_connection.arr_stop == destination:
                paths_from_here += [new_journey_to_input]
                break

            # Follow the path from the next stop
            next_stop_ends = follow_path(new_journey_to_input, destination, journey_pointers)
            paths_from_here += next_stop_ends

    return paths_from_here


def find_resulting_paths(source: int, destination: int, target_arrival: datetime,
                         journey_pointers: Dict[int, SortedJourneyList]) -> List[Journey]:
    """
    Recursively travels through the journey pointers to find paths between the source and the destination.

    :param source: the stop from which the traveller starts
    :param destination: the stop where the traveller wants to go
    :param target_arrival: the time at which the traveller needs to get there
    :param journey_pointers: the journey pointers created by the Custom Connection Scan algorithm
    :return: the possible Journeys to get from the source to the destination in time
    """
    start_journey = Journey(source, [], target_arrival)
    return follow_path(start_journey, destination, journey_pointers)
