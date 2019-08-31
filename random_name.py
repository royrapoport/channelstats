
import random
import time

fname = "random_names"

class RandomName(object):

    def __init__(self):
        firstd = {}
        lastd = {}
        f = open(fname, "r")
        for line in f.readlines():
            first, last = line.split()
            firstd[first] = 1
            lastd[last] = 1
        f.close()
        self.first = list(firstd.keys())
        self.last = list(lastd.keys())
        random.seed(time.time())
        self.used = {}
        self.collisions = 0
        self.failures = 0

    def name(self):
        attempts = 10
        while attempts:
            name = "{} {}".format(random.choice(self.first), random.choice(self.last))
            if name not in self.used:
                self.used[name] = 1
                return name
            attempts -= 1
            # print("Found collision on attempt {}".format(10 - attempts))
            self.collisions += 1
        self.failures += 1
        return name  # Oh well.  Giving up is better than failing to give a name
