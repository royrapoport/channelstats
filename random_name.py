#! /usr/bin/env python

import random
import sys
import time

fname = "random_names"

class RandomName(object):
    attempts = 50

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
        attempt = 1
        while attempt  < self.attempts:
            name = "{} {}".format(random.choice(self.first), random.choice(self.last))
            if name not in self.used:
                self.used[name] = 1
                return name
            attempt += 1
            # print("Found collision on attempt {}".format(10 - attempts))
            self.collisions += 1
        self.failures += 1
        return name  # Oh well.  Giving up is better than failing to give a name

if __name__ == "__main__":
    counter = 2000000
    if len(sys.argv) > 1:
        counter = int(sys.argv[1])
    rn = RandomName()
    for i in range(counter):
        rn.name()
    print("{} collisions ({:.1f}%)".format(rn.collisions, rn.collisions * 100.0 / counter))
    print("{} failures ({:.1f}%)".format(rn.failures , rn.failures * 100.0 / counter))
