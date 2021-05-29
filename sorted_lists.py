from typing import List

from journey_pointer import JourneyPointer


class SortedJourneyList(object):
    """ List of JourneyPointer, sorted in descending order of arrival time """

    def __init__(self, data: List[JourneyPointer]):
        self.data = data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]

    def __repr__(self):
        return f'<SortedJourneyList of size {len(self.data)}>'

    def __str__(self):
        return str(self.data)

    def append(self, e: JourneyPointer):
        """
        Adds a JourneyPoint to the list

        :param e: the element to add
        """
        for i, elem in enumerate(self.data):
            if elem.arrival_time <= e.arrival_time:
                self.data = self.data[:i] + [e] + self.data[i:]
                return
        self.data = self.data + [e]

    def remove_earliest_arrival(self):
        """ Removes the journey pointer with the earliest arrival time in the list """
        self.data = self.data[:-1]
