from datetime import datetime
from typing import List, Union, Optional, Iterable, Tuple

from connections import Footpath, TripSegment


class Journey(object):

    """ An list of Footpaths and TripSegments from a source to a destination """

    def __init__(self, source: int, paths: List[Union[Footpath, TripSegment]], target_arrival_time,
                 min_connection_time: int):
        self.paths = paths
        self.src = source
        self.target_arr_time = target_arrival_time
        self.min_co_time = min_connection_time
        self.dep_time = None
        self.arr_time = None

    def __len__(self):
        return len(self.paths)

    def __repr__(self):
        return f'<Journey of {len(self)} segments>'

    def __str__(self):
        s = f'Journey of {len(self)} segments, departs={self.departure_time()}, arrives={self.arrival_time()}'
        for p in self.paths:
            s += f'\n    {str(p)}'
        return s

    def add_segment(self, path: Union[Footpath, TripSegment]):
        self.paths.append(path)

    def changes(self) -> Iterable[Tuple[TripSegment, int]]:
        """ :return: an iterable outputting trip segments and the maximum delay that can occur """
        changes = []
        for i, segment in enumerate(self.paths):
            if isinstance(segment, TripSegment):
                # If this segment is the last one before arriving at the destination, the amount of delay that can occur
                # is the amount of time between the arrival and the time the person needs to be at the destination
                if i == len(self.paths) - 1:
                    max_delay = (self.target_arrival_time() - segment.exit_connection.arr_time).seconds // 60
                    changes.append((segment, max_delay))

                # Same if it is the segment before last but we need to walk
                elif i == len(self.paths) - 2 and isinstance(self.paths[-1], Footpath):
                    arr_time_plus_walk_time = segment.exit_connection.arr_time + self.paths[-1].walk_time
                    max_delay = (self.target_arrival_time() - arr_time_plus_walk_time).seconds // 60
                    changes.append((segment, max_delay))
                # Otherwise, it's the difference between the arrival time of this connection and the departure time of
                # the next, minus the walking time
                else:
                    next_stop_arr_time = segment.exit_connection.arr_time
                    next_connection_index = i + 1
                    if isinstance(self.paths[i + 1], Footpath):
                        next_stop_arr_time += self.paths[i + 1].walk_time
                        next_connection_index += 1
                    next_connection_dep = self.paths[next_connection_index].enter_connection.dep_time
                    max_delay = (next_connection_dep - next_stop_arr_time).seconds//60
                    changes.append((segment, max_delay))

        return changes

    def source(self) -> Optional[int]:
        return self.src

    def destination(self) -> Optional[int]:
        if len(self.paths) == 0:
            return self.src

        if isinstance(self.paths[-1], Footpath):
            return self.paths[-1].arr_stop
        else:
            return self.paths[-1].exit_stop()

    def target_arrival_time(self):
        return self.target_arr_time

    def departure_time(self) -> Optional[datetime]:
        if len(self.paths) == 0:
            return None

        if isinstance(self.paths[0], Footpath):
            if len(self.paths) == 1:
                return self.target_arrival_time() - self.paths[0].walk_time
            else:
                if not isinstance(self.paths[1], TripSegment):
                    raise ValueError(f'Two Footpaths in a row in a Journey: {self.paths}')
                return self.paths[1].departure_time - self.paths[0].walk_time
        else:
            return self.paths[0].departure_time

    def arrival_time(self) -> Optional[datetime]:
        if len(self.paths) == 0:
            return None

        if isinstance(self.paths[-1], Footpath):
            if len(self.paths) == 1:
                return self.target_arrival_time()
            else:
                if not isinstance(self.paths[-2], TripSegment):
                    raise ValueError(f'Two Footpaths in a row in a Journey: {self.paths}')
                return self.paths[-2].arrival_time + self.paths[-1].walk_time
        else:
            return self.paths[-1].arrival_time
