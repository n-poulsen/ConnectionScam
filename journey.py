from datetime import datetime, timedelta
from typing import List, Union, Optional, Iterable, Tuple, Dict, Generator

from connections import Footpath, TripSegment
from distribution import Distribution


class Journey(object):
    """
    A journey composed of Footpaths and TripSegments from a source to a destination

    Attributes:
    - :class:`List[Union[Footpath, TripSegment]]` paths --> The consecutive paths leading from the source to the
        destination
    - :class:`int` departure_stop --> The index of the train stop from which the journey starts
    - :class:`int` arrival_stop --> The index of the train stop where the journey will eventually end
    - :class:`int` current_arrival_stop --> The index of the train stop where the journey currently ends
    - :class:`Tuple[float, float, float, float]` coord --> (src_lat, src_lon, dst_lat, dst_lon)
    - :class:`float` src_lat --> The latitude of the train stop from which the journey starts
    - :class:`float` src_lon --> The longitude of the train stop from which the journey starts
    - :class:`float` dst_lat --> The latitude of the train stop where the journey ends
    - :class:`float` dst_lon --> The longitude of the train stop where the journey ends
    - :class:`datetime.datetime` target_arr_time --> The latest time at which the passenger wanted to get to the end
    - :class:`float` dst_lon --> The longitude of the train stop where the journey ends
    - :class:`int` min_co_time --> The minimum amount of time, in minutes, to "change tracks" at a stop
    """

    def __init__(self,
                 departure_stop: int,
                 arrival_stop: int,
                 coord: Tuple[float, float, float, float],
                 journey_segments: List[Union[Footpath, TripSegment]],
                 target_arrival_time: datetime,
                 min_connection_time: timedelta,
                 delay_distributions: Dict[int, Distribution],
                 arrival_time_at_last_stop: Optional[float],
                 success_probability: Optional[float]):

        self.journey_segments = journey_segments
        self.departure_stop = departure_stop
        self.arrival_stop = arrival_stop

        if len(self.journey_segments) == 0:
            self.current_arrival_stop = departure_stop
        else:
            if isinstance(self.journey_segments[-1], Footpath):
                self.current_arrival_stop = self.journey_segments[-1].arr_stop
            else:
                self.current_arrival_stop = self.journey_segments[-1].exit_connection.arr_stop

        self.reached_destination = (self.current_arrival_stop == self.arrival_stop)
        self.min_connection_time = min_connection_time

        # The segment changes in the path
        self.precomputed_changes = None

        # The success probability of the path
        if success_probability is None:
            self.chance_of_success = 1.0
        else:
            self.chance_of_success = success_probability

        # The delay distributions for different types of trips
        self.delay_distributions = delay_distributions

        # Coordinates
        self.coord = coord
        self.src_lat, self.src_lon, self.dst_lat, self.dst_lon = coord

        # Private variables
        self._departure_time = False, None
        if arrival_time_at_last_stop is not None:
            self._arrival_time = True, arrival_time_at_last_stop
        else:
            self._arrival_time = False, None
        self._target_arr_time = target_arrival_time
        self._walk_time = False, None

    def __len__(self):
        return len(self.journey_segments)

    def __repr__(self):
        return f'<Journey of {len(self)} segments>'

    def __str__(self):
        s = f'Journey of {len(self)} segments, departs={self.departure_time()}, arrives={self.current_arrival_time()}'
        for p in self.journey_segments:
            s += f'\n    {str(p)}'
        return s

    def departure_time(self) -> Optional[datetime]:
        """
        :return: the time at which the passenger needs to leave the starting point
        """
        if self._departure_time[0]:
            return self._departure_time[1]

        if len(self.journey_segments) == 0:
            self._departure_time = (True, None)
            return None

        if isinstance(self.journey_segments[0], Footpath):
            if len(self.journey_segments) == 1:
                self._departure_time = (True, None)
                return self.target_arrival_time() - self.journey_segments[0].walk_time
            else:
                if not isinstance(self.journey_segments[1], TripSegment):
                    raise ValueError(f'Two Footpaths in a row in a Journey: {self.journey_segments}')
                dep_time = self.journey_segments[1].departure_time - self.journey_segments[0].walk_time
                self._departure_time = (True, dep_time)
                return dep_time
        else:
            self._departure_time = (True, self.journey_segments[0].departure_time)
            return self._departure_time[1]

    def current_arrival_time(self) -> Optional[datetime]:
        """
        :return: the time at which the passenger arrives at the current last stop
        """
        if self._arrival_time[0]:
            return self._arrival_time[1]

        if len(self.journey_segments) == 0:
            self._arrival_time = (True, None)
            return None

        if isinstance(self.journey_segments[-1], Footpath):

            if len(self.journey_segments) == 1:
                if self.reached_destination:
                    self._arrival_time = (True, self.target_arrival_time())
                    return self.target_arrival_time()
                else:
                    self._arrival_time = (True, None)
                    return None

            else:
                if not isinstance(self.journey_segments[-2], TripSegment):
                    raise ValueError(f'Two Footpaths in a row in a Journey: {self.journey_segments}')

                arr_time = self.journey_segments[-2].arrival_time + self.journey_segments[-1].walk_time
                self._arrival_time = (True, arr_time)
                return self._arrival_time[1]

        else:
            arr_time = self.journey_segments[-1].arrival_time
            self._arrival_time = (True, arr_time)
            return self._arrival_time[1]

    def target_arrival_time(self):
        """
        :return: the time at which the passenger wants to arrive at the destination
        """
        return self._target_arr_time

    def duration(self) -> int:
        """
        :return: The journey duration, in minutes
        """
        time_diff = (self.current_arrival_time() - self.departure_time()).seconds
        return (time_diff // 60) + int(time_diff % 60 > 0)

    def walk_time(self) -> int:
        """
        :return: The amount of time that needs to be spent walking during the journey
        """
        if self._walk_time[0]:
            return self._walk_time[1]

        time: int = 0
        for segment in self.journey_segments:
            if isinstance(segment, Footpath):
                time += (segment.walk_time.seconds // 60)

        self._walk_time = True, time
        return time

    def success_probability(self) -> float:
        """
        :return: the success probability of this Journey, based on delays
        """
        return self.chance_of_success

    def changes(self) -> List[Tuple[TripSegment, int]]:
        """
        :return: an iterable outputting trip segments and the maximum delay that can occur during the journey for the
        passenger not to miss the next trip.
        """
        if self.precomputed_changes is not None:
            return self.precomputed_changes

        changes = []
        for i, segment in enumerate(self.journey_segments):
            if isinstance(segment, TripSegment):
                # If this segment is the last one before arriving at the destination, the amount of delay that can occur
                # is the amount of time between the arrival and the time the person needs to be at the destination
                if i == len(self.journey_segments) - 1:
                    max_delay = (self.target_arrival_time() - segment.exit_connection.arr_time).seconds // 60
                    changes.append((segment, max_delay))

                # Same if it is the segment before last but we need to walk
                elif i == len(self.journey_segments) - 2 and isinstance(self.journey_segments[-1], Footpath):
                    arr_time_plus_walk_time = segment.exit_connection.arr_time + self.journey_segments[-1].walk_time
                    max_delay = (self.target_arrival_time() - arr_time_plus_walk_time).seconds // 60
                    changes.append((segment, max_delay))
                # Otherwise, it's the difference between the arrival time of this connection and the departure time of
                # the next, minus the walking time
                else:
                    next_stop_arr_time = segment.exit_connection.arr_time
                    next_connection_index = i + 1
                    if isinstance(self.journey_segments[i + 1], Footpath):
                        next_stop_arr_time += self.journey_segments[i + 1].walk_time
                        next_connection_index += 1
                    next_connection_dep = self.journey_segments[next_connection_index].enter_connection.dep_time
                    max_delay = (next_connection_dep - next_stop_arr_time).seconds//60
                    changes.append((segment, max_delay))

        self.precomputed_changes = changes
        return changes


def add_segment_to_journey(j: Journey, new_segment: Union[Footpath, TripSegment]) -> Journey:
    """

    :param j:
    :param new_segment:
    :return: A copy of the journey with the added segment
    """
    new_journey_segments = j.journey_segments.copy()
    new_journey_segments.append(new_segment)
    new_success_probability = j.success_probability()
    new_arrival_time_at_last_stop = None

    if isinstance(new_segment, Footpath):
        # If we haven't arrived, we don't know at what time the next connection is yet.
        # Otherwise we know at what time we needed to be there
        if new_segment.arr_stop == j.arrival_stop:
            # If the journey didn't have an arrival time, then the chance of making this trip is 1.
            # Otherwise we need to compute the probability to arrive at the destination in time
            if j.current_arrival_time() is not None:
                time_to_arrive = j.current_arrival_time() + new_segment.walk_time
                max_delay = (j.target_arrival_time() - time_to_arrive).seconds // 60
                # The probability to arrive in time is based on the probability distribution of the last trip segment
                previous_trip = j.journey_segments[-1]
                last_trip_distribution = j.delay_distributions.get(previous_trip.delay_distribution_id())
                new_success_probability = new_success_probability * last_trip_distribution.cdf(max_delay)

                new_arrival_time_at_last_stop = previous_trip.arrival_time + new_segment.walk_time
            else:
                # If we didn't have a minimum arrival time, than we can arrive at the last stop at the target
                new_arrival_time_at_last_stop = j.target_arrival_time()

    else:
        # Compute the probability of arriving at the stop before the connection leaves.
        # 1 if there is no current arrival time for the journey
        if j.current_arrival_time() is not None:
            if isinstance(j.journey_segments[-1], TripSegment):
                previous_trip = j.journey_segments[-1]
                arrival_time_at_new_connection = previous_trip.arrival_time
            else:
                previous_trip = j.journey_segments[-2]
                arrival_time_at_new_connection = previous_trip.arrival_time + j.journey_segments[-1].walk_time

            last_trip_distribution = j.delay_distributions.get(previous_trip.delay_distribution_id())
            max_delay = (new_segment.departure_time - arrival_time_at_new_connection).seconds // 60
            new_success_probability *= last_trip_distribution.cdf(max_delay)

        new_arrival_time_at_last_stop = new_segment.arrival_time

    extended_journey = Journey(
        j.departure_stop,
        j.arrival_stop,
        j.coord,
        new_journey_segments,
        j.target_arrival_time(),
        j.min_connection_time,
        j.delay_distributions,
        new_arrival_time_at_last_stop,
        new_success_probability,
    )

    return extended_journey
