#!/usr/bin/python

import sys, time, snap
import scipy.sparse as sp
import scipy.sparse.linalg as linalg
from util import pickler
from collections import defaultdict
import numpy as np


def generateFeatures(year, bipartite, unipartite, newToOldIDs, adjMatrix):

    start = time.time()

    bipartiteFeatures = extractBipartiteFeatures(bipartiteGraph)
    print '  Finished extracting bipartite features. Time from start of weight-cycle: %d' % (time.time() - start)

    unipartiteFeatures = convertNewToOldIDs(extractUnipartiteFeatures(unipartiteGraph, adjMatrix), newToOldIDs)
    print '  Finished extracting unipartite features. Time from start of weight-cycle: %d' % (time.time() - start)

    # append unipartite features to bipartite features for each node, returning combined feature dictionary:
    features = {}
    for oldNID in unipartiteFeatures:
        features[oldNID] = bipartiteFeatures[oldNID] + unipartiteFeatures[oldNID]
    print '  Finished combining unipartite and bipartite features. Time from start of weight-cycle: %d' % (time.time() - start)

    return features


def extractBipartiteFeatures(bipartiteGraph):

    features = defaultdict(list)
    numDonations, totalAmount, cands, transactions, amounts = getDonorInfos(bipartiteGraph)

    for i, node in enumerate(bipartiteGraph.Nodes()):
        nid = node.GetId()
        if nid not in totalAmount:
            continue

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
    start = time.time()

    features = defaultdict(list)
    getUnipartiteSurfaceFeatures(unipartiteGraph, adjMat, features)

    print '    1. Finished extracting surface features after: %d' % (time.time() - start)

    # Average weight of edges:
    # weightSums = adjMat.sum(axis=1)
    # rows, cols = adjMat.nonzero()
    # avgWeightDenoms = [0.0] * unipartiteGraph.GetNodes()
    # for r in rows:
    #     avgWeightDenoms[r] += 1.0
    # avgWeights = weightSums / avgWeightDenoms
    # zeros = [i for i in range(len(weightSums)) if weightSums[i] == 0]
    # print zeros
    # avgWeights[zeros] = 1 / len(avgWeights)

    print '    2. Finished computing average weights after: %d' % (time.time() - start)

    # Size of connected component:
    cnctComponents = calcCnctComponents(unipartiteGraph)

    print '    3. Finished computing connected components after: %d' % (time.time() - start)

    # Node clustering coefficients:
    # NIdCCfH = snap.TIntFltH()
    # snap.GetNodeClustCf(unipartiteGraph, NIdCCfH)

    # print '4. Finished computing clustering coefficients after: %d' % (time.time() - start)

    # Eigenvectors:
    eigenVal, eigenVecs = sp.linalg.eigs(adjMat, k=1)

    print '    5. Finished computing eigenvectors after: %d' % (time.time() - start)

    # Pagerank:
    pageRanks = snap.TIntFltH()
    snap.GetPageRank(unipartiteGraph, pageRanks)

    print '    6. Finished computing pagerank after: %d' % (time.time() - start)

    # combine the graph wide features with the existing surface features:
    for nid in features:
        # features[nid].append(avgWeights[nid])
        features[nid].append(cnctComponents[nid])
        # features[nid].append(NIdCCfH[nid])
        features[nid].append(float(eigenVecs[nid][0]))
        features[nid].append(pageRanks[nid])

    print '    Finally finished aggregating features into one unipartite vector after: %d' % (time.time() - start)

    return features

# Takes the graph and adjacency matrix, and uses these to update the
# features map for the unipartite graph.
def getUnipartiteSurfaceFeatures(graph, adjMat, features):

    for i, node in enumerate(graph.Nodes()):
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


if __name__ == '__main__':
    for year in range(1980, 1982, 2):

        print '*************** Starting cycle: %d ***************' % year
        start = time.time()

        bipartiteGraph = snap.TNEANet.Load(snap.TFIn('Data/Bipartite-Graphs/%d.graph' % year))
        unipartiteGraph = snap.TUNGraph.Load(snap.TFIn('Data/Unipartite-Graphs/%d.graph' % year))
        newToOldIDs = pickler.load('Data/Unipartite-NodeMappings/%d.newToOld' % year)
        print 'Finished loading input graphs/matrices for cycle. Time taken: %d' % (time.time() - start)

        for weightF in ['jaccard', 'affinity', 'jaccard2']:
            print '---------------------------------------'
            print 'Starting %d: %s' % (year, weightF)

            adjMatrix = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
            adjMatrix = adjMatrix.tocsc()

            features = generateFeatures(year, bipartiteGraph, unipartiteGraph, newToOldIDs, adjMatrix)
            pickler.save(features, 'Data/Features/%d%s.features' % (year, weightF))

            print 'Finished %d: %s' % (year, weightF)

        print 'Total time taken for this cycle: %d' % (time.time() - start)
