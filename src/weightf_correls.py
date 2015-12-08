#!/usr/bin/python
# Module: weightf_correls
# Generates a correlation matrix between the weights given by all of the weighting
# functions.

import sys
import numpy as np
from util import pickler
from util.Timer import Timer

################################################################################
# Module functions #
################################################################################

# Loads the adjacency matrix for a particular year-weight function pairing and
# returns a vector of all the nonzero entries for that matrix.
# Return format is 1 x N numpy array (NOT vector)
def getNonzeroElems(year, weightF):
    timing = Timer('Loading nonzero elems for year %d and weightf %s ' % (year, weightF))
    adjMat = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
    timing.finish()
    return adjMat[adjMat.nonzero()]

# Actually generates the correlatiion matrix. We can afford to simpy call the
# nonzero function of each adjacency matrix individually (as opposed to caching
# a single common set of indices) since we know that all the adjacency matrices
# have the same set of nonzero indices (namely, the donors that had at least
# one candidate in common).
def getCorrel(year, weightFs):
    timing = Timer('Getting correlation matrix for year %d' % year)
    append = lambda x, y: np.append(x, y, axis=0)
    data = reduce(append, [getNonzeroElems(year, weightF) for weightF in weightFs])
    timing.finish()
    return np.corrcoef(data)

################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    weightFs = ('affinity', 'cosine', 'jaccard', 'jaccard2', 'adamic', 'weighted_adamic')
    for arg in sys.argv[1:]:
        year = int(arg)
        cov = getCorrel(year, weightFs)
        print 'Correlation matrix for %d:' % year
        print cov

