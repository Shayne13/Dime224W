import snap, sys
import numpy as np
from util import pickler, graph_funcs
from util.Timer import Timer

################################################################################
# Module functions #
################################################################################

# Given a file for a sparse weighted adjacency matrix, returns a list of node
# index pairs and their adjacency weighting.
# The return value is a list of tuples where the first two elements are the
# smaller and larger node id and the third element is the weighting. Also
# returns the number of nodes to be inserted into the new graph.
def getSortedMatrixVals(filename):
    timing = Timer('Gettin sorted matrix vals')
    adjMat = pickler.load(filename)
    timing.markEvent('Loaded adjacency matrix')
    N = adjMat.shape[0]
    xIndices, yIndices = adjMat.nonzero()
    timing.markEvent('Loaded nonzero indices')
    data = adjMat[xIndices, yIndices]
    timing.markEvent('Loaded nonzero vals')
    flat = np.ravel(data)
    timing.markEvent('Flattened data')

    vals = zip(xIndices, yIndices, flat)
    timing.markEvent('Zipped values')
    vals.sort(key=lambda v: v[2], reverse=True)
    timing.markEvent('Sorted values')
    return vals, N

# Given the vals from getSortedMatrixVals, the number of nodes, and a percent
# threshold, creates a graph whose edges are those with the (percent)% highest
# weights.
def pruneGraphByPercent(sortedVals, N, percent):
    numEdges = int(len(sortedVals) * percent)
    graph = snap.TUNGraph.New(N, numEdges)

    for i in range(N):
        graph.AddNode()

    for n1, n2, weight in sortedVals[:numEdges]:
        graph.AddEdge(int(n1), int(n2))

    return graph

# Given the vals from getSortedMatrixVals, the number of nodes, and a weight
# threshold that must be met, creates a graph whose edges are those with weights
# at least meeting the threshold.
def pruneGraphByThreshold(sortedVals, N, threshold):
    graph = snap.TUNGraph.New(N, N)

    for i in range(N):
        graph.AddNode()

    for n1, n2, weight in sortedVals:
        if weight < threshold:
            break
        graph.AddEdge(int(n1), int(n2))

    return graph

# Given a year, a weighting function, and lists of percentages and thresholds
# to generate graphs for, generates graphs and saves them to
# Data/Unipartite-Graphs with a filename indicating the parameters.
def processYearAndWeight(year, weighting, percents=None, thresholds=None):
    timing = Timer('Running for year %d and weight %s' % (year, weighting))
    adjMatFile = 'Data/Unipartite-Matrix/%d.%s' % (year, weighting)
    sortedVals, N = getSortedMatrixVals(adjMatFile)
    timing.markEvent('Got sorted vals')

    if percents:
        for p in percents:
            outfile = 'Data/Unipartite-Graphs/%d.%s_percent_%f.graph' \
                    % (year, weighting, p)
            graph = pruneGraphByPercent(sortedVals, N, p)
            graph_funcs.saveGraph(graph, outfile)
            timing.markEvent('Finished for %f percent' % p)

    if thresholds:
        for t in thresholds:
            outfile = 'Data/Unipartite-Graphs/%d.%s_threshold_%f.graph' \
                    % (year, weighting, t)
            graph = pruneGraphByThreshold(sortedVals, N, t)
            graph_funcs.saveGraph(graph, outfile)
            timing.markEvent('Finished for threshold %f' % t)

    timing.finish()

################################################################################
# Command-line behavior #
################################################################################

if __name__ == '__main__':
    # Use standard percentage thresholds
    percents = [0.01, 0.05, 0.1, 0.25, 0.5]

    # Dictionary from weighting function to the thresholds we'll use (based on
    # pdf and cdf plots for that weight)
    thresholdsDict = {
        'adamic': [np.exp(-1.5), np.exp(-1), 1],
        'cosine': [0.8, 0.95, 0.99],
        'jaccard': [0.05, 0.1, 0.2],
        'jaccard2': [0.05, 0.1, 0.2],
        'weighted_adamic': [np.exp(6), np.exp(8), np.exp(9)],
    }

    for arg in sys.argv[1:]:
        year = int(arg)
        for weighting, thresholds in thresholdsDict.iteritems():
            processYearAndWeight(year, weighting, percents, thresholds)
