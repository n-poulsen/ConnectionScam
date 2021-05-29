from datetime import datetime, timedelta


class Connection(object):
    """ A connection in the graph """

    def __init__(self, trip_id: str, ttype: str, dep_stop: int, arr_stop: int, dep_lat: float, dep_lon: float,
                 arr_lat: float, arr_lon: float, dep_time: datetime, arr_time: datetime):
        # Trip information
        self.trip_id = trip_id
        self.transport_type = ttype

        # Departure and arrival stop indices
        self.dep_stop = dep_stop
        self.arr_stop = arr_stop

        # Departure and arrival stop latitudes and longitudes
        self.dep_lat = dep_lat
        self.dep_lon = dep_lon
        self.arr_lat = arr_lat
        self.arr_lon = arr_lon

        # Departure and arrival times
        self.dep_time = dep_time
        self.arr_time = arr_time

    def __repr__(self):
        return f'<Connection ({self.dep_stop} -> {self.dep_stop}), ({self.dep_time} -> {self.arr_time})>'

    def __str__(self):
        return f'{self.transport_type} Connection on trip {self.trip_id}' \
               f' from ({self.dep_stop} -> {self.dep_stop})' \
               f' at ({self.dep_time} -> {self.arr_time})'


class TripSegment(object):

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
        return self.enter_connection.dep_stop

    def exit_stop(self) -> int:
        return self.exit_connection.arr_stop

    def entry_stop_lat(self) -> float:
        return self.enter_connection.dep_lat

    def entry_stop_lon(self) -> float:
        return self.enter_connection.dep_lon

    def exit_stop_lat(self) -> float:
        return self.exit_connection.arr_lat

    def exit_stop_lon(self) -> float:
        return self.exit_connection.arr_lon


class Footpath(object):
    """ A footpath in the graph """

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
