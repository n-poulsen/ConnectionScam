

class Distribution(object):
    def __init__(self, times: list, probas: list, distr_id: int):
        """
        Creates a distribution object

        Arguments
        =========
        times : list of int
            list of delays in minutes.
        probas : list of float
            list of probability to get the delays in times.
            Same size as times.
        distr_id : int
            Identifier of the distribution

        Raises
        ======
        ValueError
            Raised if the lists times and probas are of different lengths
        """
        if len(times) != len(probas):
            raise ValueError("The times and probas have to contain the same number of elements")

        self.times = times
        self.probas = probas
        self.id = distr_id

    def __str__(self):
        return 'Distribution [{}], {} values'.format(self.id, len(self.times))

    def __repr__(self):
        return '<Distribution {}>'.format(self.id)

    def cdf(self, delay: int):
        """
        Calculates the CDF of having at most the given delay

        Argument
        ========
        delay : int
            Delay in minutes

        Returns
        =======
        float
            Probability of having a delay less or equal to the given delay.
        """
        if delay < 0:
            raise VaueError("The delay of a CDF has to be non-negative, got {}".format(delay))
        return sum([self.probas[i] for i, t in enumerate(self.times) if t <= delay], 0)
