from datetime import datetime
from typing import Optional

from connections import Connection, Footpath


class JourneyPointer(object):
    """
    Pointers used to reconstruct the journey from the source to the sink

    Attributes:

    - :class:`datetime` arrival_time --> The latest time at which someone can
        arrive at the stop to make the connection.
    - :class:`Optional[Connection]` enter_connection --> If none, then this
        journey is a simple walk from a node to the sink. Otherwise, this is
        the connection from the
    - :class:`Optional[Connection]` exit_connection --> The name of the test object
    - :class:`Footpath` footpath --> The name of the test object
    """

    def __init__(self,
                 arrival_time: datetime,
                 enter_connection: Optional[Connection],
                 exit_connection: Optional[Connection],
                 footpath: Optional[Footpath]):

        self.arrival_time = arrival_time
        self.enter_connection = enter_connection
        self.exit_connection = exit_connection
        self.footpath = footpath

    def __repr__(self):
        return f'<JourneyPointer ({self.arrival_time.time()}, {self.enter_connection}, ' \
               f'{self.exit_connection}, {self.footpath})>'

    def __str__(self):
        return f'({self.arrival_time.time()}, {self.enter_connection}, {self.exit_connection}, {self.footpath})'
