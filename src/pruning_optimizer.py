#!/usr/bin/python
# Script: pruning_optimizer
# Generates features and runs regressions for every pruned unipartite graph.
# Yields the pruned unigraph with the highest average KFold r^2 with OLS and
# no factor decomposition

import sys, snap, feature_extractor, recip_feature_extractor, cfscore_predictions
from os import listdir
from util import pickler, graph_funcs
from util.Timer import Timer
import numpy as np

# Get all the pruned unipartite graph files with this weight function
def getGraphFiles(year, weightF):
    return [f for f in listdir('Data/Unipartite-Graphs/') \
            if f.startswith('%d.%s_' % (year, weightF))]

# Saves the donor features for all the pruned graphs with this weight function.
def genDonorFeatures(year, weightF, graphFiles=None, bigraph=None, adjMat=None, newToOldIDs=None):
    timing = Timer('Generating donor features for %d %s' % (year, weightF))

    if not graphFiles:
        graphFiles = getGraphFiles(year, weightF)
    if not bigraph:
        bigraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)
    if adjMat is None:
        adjMat = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
        adjMat = adjMat.tocsc()
    if newToOldIDs is None:
        newToOldIDs = pickler.load('Data/Unipartite-NodeMappings/%d.newToOld' % year)
    timing.markEvent('Loaded bigraph, adj matrix, and newToOld mapping')

    for gf in graphFiles:
        unigraph = graph_funcs.loadGraph('Data/Unipartite-Graphs/%s' % gf, snap.TUNGraph)
        timing.markEvent('Loaded graph %s' % gf)

        features = feature_extractor.generateFeatures(year, bigraph, unigraph, newToOldIDs, adjMat)
        timing.markEvent('Generated features')

        pickler.save(features, 'Data/Features/%s.features' % gf)
        timing.markEvent('Saved features')

    timing.finish()

# Saves the recipient features for all the pruned donor features with this weight
# function.
def genRecipFeatures(year, weightF, graphFiles=None, bigraph=None):
    timing = Timer('Generating recip features for %d %s' % (year, weightF))

    if not graphFiles: graphFiles = getGraphFiles(year, weightF)
    if not bigraph: bigraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)

    receiptsFromDonor, totalReceipts, totalDonations = \
            recip_feature_extractor.getDonationAmounts(bigraph)
    partialFeatures, fullFeatures = \
            recip_feature_extractor.getCategoricalGraphFeatures(bigraph)

    timing.markEvent('Loaded bigraph, donor amounts, and categorical feature funcs')

    for gf in graphFiles:
        donorFeatures = pickler.load('Data/Features/%s.features' % gf)
        timing.markEvent('Loaded donor features for graph %s' % gf)

        recipFeatures = recip_feature_extractor.getRecipFeatures(
                bigraph, donorFeatures, receiptsFromDonor, totalReceipts,
                totalDonations, partialFeatures, fullFeatures)
        timing.markEvent('Calculated recip features')

        recip_feature_extractor.saveFeatures(bigraph, recipFeatures, 'Data/Recip-Features/%s' % gf)
        timing.markEvent('Saved recip features')

    timing.finish()

# Returns the regression results for all the pruned recip features with this
# weight function.
def getResults(year, weightF, graphFiles=None):
    timing = Timer('Running regressions for %d %s' % (year, weightF))

    results = []

    if not graphFiles: graphFiles = getGraphFiles(year, weightF)

    for gf in graphFiles:
        X, Y = pickler.load('Data/Recip-Features/%s' % gf)
        rsquareds = cfscore_predictions.trainAndTestModels(year, weightF, X=X, Y=Y)
        results.append([weightF, gf, rsquareds])

    timing.finish()

    return results

def runFullPipeline(year):
    timing = Timer('Running pipeline for %d' % year)

    weightings = ('adamic', 'cosine', 'jaccard', 'jaccard2', 'weighted_adamic')
    bigraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph'% year)
    newToOldIDs = pickler.load('Data/Unipartite-NodeMappings/%d.newToOld' % year)

    for weightF in weightings:

        graphFiles = getGraphFiles(year, weightF)

        adjMat = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
        timing.markEvent('Loaded everything for donor features')
        genDonorFeatures(year, weightF, graphFiles=graphFiles, bigraph=bigraph,\
                adjMat=adjMat, newToOldIDs=newToOldIDs)
        del adjMat # free the incredible amount of memory for the adjacency matrix


        genRecipFeatures(year, weightF, graphFiles=graphFiles, bigraph=bigraph)
        results = getResults(year, weightF, graphFiles=graphFiles)
        pickler.save(results, 'Data/pruning_optimizations.%d.%s' % (year, weightF))
        timing.markEvent('Finished with %s' % weightF)

    timing.finish()

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        year = int(arg)
        runFullPipeline(year)

