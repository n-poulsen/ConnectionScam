from datetime import datetime, timedelta


class Connection(object):
    """
    A public transport vehicle driving from one stop to another stop without an intermediate halt during a trip.

    Attributes:
    - :class:`Any` trip_id --> the id of the trip to which this segment belongs.
    - :class:`str` transport_type --> type of transport along this trip (e.g., 'train', 'bus', ...)
    - :class:`int` dep_stop --> the index of the departure stop of the connection
    - :class:`int` arr_stop --> the index of the arrival stop of the connection
    - :class:`datetime.datetime` dep_time --> the time at which the connection leaves the departure stop
    - :class:`datetime.datetime` arr_time --> the time at which the connection arrives to the arrival stop
    - :class:`int` distribution_id --> the delay distribution id for this connection
    """

    def __init__(self, trip_id: str, ttype: str, dep_stop: int, arr_stop: int, dep_time: datetime, arr_time: datetime,
                 distribution_id: int):
        # Trip information
        self.trip_id = trip_id
        self.transport_type = ttype

        # Departure and arrival stop indices
        self.dep_stop = dep_stop
        self.arr_stop = arr_stop

        # Departure and arrival times
        self.dep_time = dep_time
        self.arr_time = arr_time

        # Delay distribution group
        self.distribution_id = distribution_id

    def __repr__(self):
        return f'<Connection ({self.dep_stop} -> {self.dep_stop}), ({self.dep_time} -> {self.arr_time})>'

    def __str__(self):
        return f'{self.transport_type} Connection on trip {self.trip_id}' \
               f' from ({self.dep_stop} -> {self.dep_stop})' \
               f' at ({self.dep_time} -> {self.arr_time})'


class TripSegment(object):
    """
    A consecutive subset of a trip taken by a user (i.e., boarding a train at stop i and getting off at stop j)

    Attributes:
    - :class:`Any` trip_id --> the id of the trip to which this segment belongs.
    - :class:`str` transport_type --> type of transport along this trip (e.g., 'train', 'bus', ...)
    - :class:`Connection` enter_connection --> the first connection in the trip that the user takes
    - :class:`Connection` exit_connection --> the last connection in the trip that the user takes
    - :class:`datetime.datetime` departure_time --> the departure time of the segment
    - :class:`datetime.datetime` arrival_time --> the arrival time of the segment
    """

    def __init__(self, enter_connection: Connection, exit_connection: Connection):
        self.trip_id = enter_connection.trip_id
        self.transport_type = enter_connection.transport_type
        self.enter_connection = enter_connection
        self.exit_connection = exit_connection
        self.departure_time = enter_connection.dep_time
        self.arrival_time = exit_connection.arr_time

    def __repr__(self):
        return f'<TripSegment ({self.trip_id}, {self.enter_connection.dep_stop} -> {self.exit_connection.arr_stop})>'

    def __str__(self):
        s = f'TripSegment of trip {self.trip_id}'
        s += f'  from {self.enter_connection.dep_stop} to {self.exit_connection.arr_stop}'
        s += f'  departure {self.enter_connection.dep_time}, arrival {self.exit_connection.arr_time}'
        return s

    def entry_stop(self) -> int:
        """
        :return: the stop at which the user boards the trip
        """
        return self.enter_connection.dep_stop

    def exit_stop(self) -> int:
        """
        :return: the stop at which the user exits the trip
        """
        return self.exit_connection.arr_stop

    def delay_distribution_id(self) -> int:
        """
        :return: the delay distribution id for the arrival connection of the trip segment
        """
        return self.exit_connection.distribution_id


class Footpath(object):
    """
    A path that people can take on foot between two public transportation stops.

    Attributes:
    - :class:`int` dep_stop --> the index of the departure stop of the footpath
    - :class:`int` arr_stop --> the index of the arrival stop of the footpath
    - :class:`datetime.timedelta` walk_time --> the duration it takes to walk between the stops.
    """

    def __init__(self, dep_stop: int, arr_stop: int, walk_time: timedelta):
        # Departure and arrival stop indices
        self.dep_stop = dep_stop
        self.arr_stop = arr_stop

        # Walk time between the stops
        self.walk_time = walk_time

    def __repr__(self):
        return f'<Footpath ({self.dep_stop} -> {self.arr_stop}), {self.walk_time}>'

    def __str__(self):
        return f'Footpath from {self.dep_stop} to {self.arr_stop}, {self.walk_time.seconds//60} minutes'
