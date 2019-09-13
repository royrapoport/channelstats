#! /usr/bin/env python

import random
import sys
import time

fname = "words"

class RandomChannel(object):
    attempts = 50

    def __init__(self):
        f = open(fname, "r")
        self.words = []
        for line in f.readlines():
            word = line.strip()
            self.words.append(word)
        f.close()
        random.seed(time.time())
        self.used = {}
        self.collisions = 0
        self.failures = 0

    def name(self):
        attempt = 1
        while attempt  < self.attempts:
            if random.choice(range(2)):
                # Create a SOMETHING-and/or-SOMETHING
                middle = "and"
                if random.choice(range(2)):
                    middle = "or"
                name = "{}-{}-{}".format(random.choice(self.words), middle, random.choice(self.words))
            else:
                name = random.choice(self.words)
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
    rn = RandomChannel()
    for i in range(counter):
        rn.name()
    print("{} collisions ({:.1f}%)".format(rn.collisions, rn.collisions * 100.0 / counter))
    print("{} failures ({:.1f}%)".format(rn.failures , rn.failures * 100.0 / counter))
