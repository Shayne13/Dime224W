#!/usr/bin/python

import sys, snap
import scipy.sparse as sp
import scipy.sparse.linalg as linalg
from util import pickler, graph_funcs
from util.Timer import Timer
from collections import defaultdict
import numpy as np


def generateFeatures(year, bipartite, unipartite, newToOldIDs, adjMatrix):
    timing = Timer('generating features for %d' % year)

    bipartiteFeatures = extractBipartiteFeatures(bipartiteGraph)
    timing.markEvent('Extracted bipartite features.')

    unipartiteFeatures = convertNewToOldIDs(extractUnipartiteFeatures(unipartiteGraph, adjMatrix), newToOldIDs)
    timing.markEvent('Extracted unipartite features.')

    # append unipartite features to bipartite features for each node, returning combined feature dictionary.
    # If the donor is not in the unipartite feature graph then we just take the default values (since the 
    # node falls below the unipartite threshold from sqlToGraphs):
    features = {}
    for donorNode in graph_funcs.getDonors(bipartite):
        oldNID = donorNode.GetId()
        if oldNID in unipartiteFeatures:
            features[oldNID] = bipartiteFeatures[oldNID] + unipartiteFeatures[oldNID]
        else:
            features[oldNID] = bipartiteFeatures[oldNID] + defaultUnipartiteFeatures()
    timing.finish()

    return features


def extractBipartiteFeatures(bipartiteGraph):

    features = defaultdict(list)
    numDonations, totalAmount, cands, transactions, amounts = getDonorInfos(bipartiteGraph)

    for node in graph_funcs.getDonors(bipartiteGraph):
        nid = node.GetId()

        # Total amount donated:
        features[nid].append(totalAmount[nid])

        # Total number of candidates donated to (MULTICOLLINEARITY WARNING):
        features[nid].append(len(cands[nid]))

        # Percent of donations to Democrats:
        demRecipIDs = [rid for rid in cands[nid] if (bipartiteGraph.GetIntAttrDatN(rid, 'party') == 1)]
        amountToDems = sum([amounts[nid][rid] for rid in demRecipIDs])
        features[nid].append(amountToDems / float(totalAmount[nid]))

    return features


def extractUnipartiteFeatures(unipartiteGraph, adjMat):
    timing = Timer('extracting unipartite features')

    features = defaultdict(list)
    getUnipartiteSurfaceFeatures(unipartiteGraph, adjMat, features)

    timing.markEvent('1. Extracted surface features')

    # Average weight of edges:
    # weightSums = adjMat.sum(axis=1)
    # rows, cols = adjMat.nonzero()
    # avgWeightDenoms = [0.0] * unipartiteGraph.GetNodes()
    # for r in rows:
    #     avgWeightDenoms[r] += 1.0
    # avgWeights = weightSums / avgWeightDenoms
    # zeros = [i for i in range(len(weightSums)) if weightSums[i] == 0]
    # avgWeights[zeros] = 1.0 / len(avgWeights)
    timing.markEvent('2. Computed average weights.')

    # Size of connected component:
    cnctComponents = calcCnctComponents(unipartiteGraph)
    timing.markEvent('3. Computed connected components.')

    # Node clustering coefficients:
    # NIdCCfH = snap.TIntFltH()
    # snap.GetNodeClustCf(unipartiteGraph, NIdCCfH)
    timing.markEvent('4. Computed clustering coefficients.')

    # Eigenvectors:
    # eigenVal, eigenVec = sp.linalg.eigs(adjMat, k=1)
    timing.markEvent('5. Computed eigenvectors.')

    # Pagerank:
    pageRanks = snap.TIntFltH()
    snap.GetPageRank(unipartiteGraph, pageRanks)
    timing.markEvent('6. Computed PageRank.')

    # combine the graph wide features with the existing surface features:
    for nid in features:
        # features[nid].append(avgWeights[nid])
        features[nid].append(cnctComponents[nid])
        # features[nid].append(NIdCCfH[nid])
        # features[nid].append(float(eigenVec[nid][0]))
        features[nid].append(pageRanks[nid])

    timing.finish()

    # print 'Eigenvector check:'
    # print 'min: ' + str(np.min(eigenVec)) + ' goes to ' + str(float(np.min(eigenVec)))
    # print 'max: ' + str(np.max(eigenVec)) + ' goes to ' + str(float(np.max(eigenVec)))
    # print 'eigenval: ' + str(eigenVal)


    return features

# Takes the graph and adjacency matrix, and uses these to update the
# features map for the unipartite graph.
def getUnipartiteSurfaceFeatures(graph, adjMat, features):

    for node in graph.Nodes():
        nid = node.GetId()

        # Node degree:
        features[nid].append(node.GetDeg())

        # Nodes at hop:
        # nodesAtHop = snap.TIntV()
        # features[nid].append(snap.GetNodesAtHop(graph, nid, 2, nodesAtHop, False))


# Efficiently computes the connected components of the graph returning
# a dictionary: { nid -> lenComp }
def calcCnctComponents(graph):
    lenComps = {}
    CnCom = snap.TIntV()
    for node in graph.Nodes():
        nodeid = node.GetId()
        if nodeid in lenComps:
            continue
        snap.GetNodeWcc(graph, nodeid, CnCom)
        l = CnCom.Len()
        lenComps[nodeid] = l
        for conNode in CnCom:
            lenComps[conNode] = l

    return lenComps


# Given a bipartite donor-candidate graph, returns 5 relevant dictionaries
# from cnodeids to various donation metrics. These are, in order,
# 1. The total number of donations that donor made
# 2. The total amount that donor donated
# 3. The set of rnodeids that donor gave to
# 4. A dictionary showing how many donations the donor made to each rnodeid
# 5. A dictionary showing how much the donor gave to each rnodeid
def getDonorInfos(graph):
    # Dict from cnodeids to ints showing how many donations this person has made
    numDonations = defaultdict(int)

    # Dict from cnodeids to ints showing how much money this person has donated
    totalAmount = defaultdict(int)

    # Dict from cnodeids to set of ints showing which nodes received donations
    # from this donor
    cands = defaultdict(set)

    # Dict from cnodeids to dict from rnodeids to ints showing the number of
    # donations from that donor node to that recipient node
    transactions = defaultdict(lambda: defaultdict(int))

    # Dict from cnodeids to dict from rnodeids to ints showing the amount
    # donated by that donor to that recipient
    amounts = defaultdict(lambda: defaultdict(int))

    # Add each edge's info to the dicts
    for edge in graph.Edges():
        cnodeid = edge.GetSrcNId()
        rnodeid = edge.GetDstNId()
        amount = graph.GetIntAttrDatE(edge, 'amount')

        numDonations[cnodeid] += 1
        totalAmount[cnodeid] += amount
        cands[cnodeid].add(rnodeid)
        transactions[cnodeid][rnodeid] += 1
        amounts[cnodeid][rnodeid] += amount

    return numDonations, totalAmount, cands, transactions, amounts

# Takes in the { unipartiteNodeIDs -> [features] } and newToOldID mapping
# and returns { bipartiteNodeIDs -> [features] }.
def convertNewToOldIDs(newIDFeatureMapping, newToOldIDs):
    oldIDFeatureMapping = {}

    for newID in newIDFeatureMapping:
        oldIDFeatureMapping[newToOldIDs[newID]] = newIDFeatureMapping[newID]

    return oldIDFeatureMapping

# The default unipartite features for a node not in the unipartite graph:
def defaultUnipartiteFeatures():
    defaultFeatures = []
    defaultFeatures.append(0.0) # degree
    # defaultFeatures.append() # nodes at hop 2
    # defaultFeatures.append(0) # avg. weight of edges
    defaultFeatures.append(1.0) # size of connected component
    # defaultFeatures.append(0.0) # clustering coefficient
    # defaultFeatures.append(0.0) # eigenvector value
    defaultFeatures.append(0.0) # pagerank score
    return defaultFeatures


if __name__ == '__main__':
    for year in range(1980, 1982, 2):
        print 
        timing = Timer('creating unipartite graph for %d' % year)

        bipartiteGraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)
        unipartiteGraph = graph_funcs.loadGraph('Data/Unipartite-Graphs/%d.graph' % year, snap.TUNGraph)
        newToOldIDs = pickler.load('Data/Unipartite-NodeMappings/%d.newToOld' % year)
        timing.markEvent('Loaded input graphs/matrices.')

        for weightF in ['jaccard', 'affinity', 'jaccard2']:
            print '******* %s *******' % weightF
            adjMatrix = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
            adjMatrix = adjMatrix.tocsc()

            features = generateFeatures(year, bipartiteGraph, unipartiteGraph, newToOldIDs, adjMatrix)
            pickler.save(features, 'Data/Features/%d%s.features' % (year, weightF))

            timing.markEvent('Processed %s weight function' % weightF)

        timing.finish()


# Features:

# 1. degree 
# 2. nodes at hop 2
# 3. avg. weight of edges
# 4. size of connected component
# 5. categorical label of connected component
# 6. clustering coefficient
# 7. eigenvector value
# 8. pagerank score