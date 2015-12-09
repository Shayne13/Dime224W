#!/usr/bin/python
# Module: feature_extractor
# To call from the command line, run `python src/feature_extractor <years>`, where
# <years> contains each year whose graph you want to generate.

import sys, snap
import scipy.sparse as sp
import scipy.sparse.linalg as linalg
from util import pickler, graph_funcs, categorical
from util.Timer import Timer
from collections import defaultdict
import numpy as np


def generateFeatures(year, bipartite, unipartite, newToOldIDs, adjMatrix):
    timing = Timer('generating features for %d' % year)

    bipartiteFeatures = extractBipartiteFeatures(bipartiteGraph)
    timing.markEvent('Extracted bipartite features.')

    # rawUnifeatures, componentFeatureFunc, communityFeatureFuncn = extractUnipartiteFeatures(unipartiteGraph, adjMatrix)
    rawUnifeatures, componentFeatureFunc, CNMFeatureFunc = extractUnipartiteFeatures(unipartiteGraph, adjMatrix)
    unipartiteFeatures = convertNewToOldIDs(rawUnifeatures, newToOldIDs)
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
            features[oldNID] = bipartiteFeatures[oldNID] + defaultUnipartiteFeatures(componentFeatureFunc, CNMFeatureFunc) #, communityFeatureFuncn)
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

# Returns both the dictionary from unipartite node id to feature vector AND the categorical
# feature func for connected component ID.
# TODO: Fix this decomp.
def extractUnipartiteFeatures(unipartiteGraph, adjMat):
    timing = Timer('extracting unipartite features')

    features = defaultdict(list)
    #componentFeatureFunc, communityFeatureFuncn, idToCommunity = getUnipartiteSurfaceFeatures(unipartiteGraph, adjMat, features)
    componentFeatureFunc, CNMFeatureFunc, idToCNM = getUnipartiteSurfaceFeatures(unipartiteGraph, adjMat, features)

    timing.markEvent('1. Extracted surface features')

    # Average weight of edges:
    #avgWeights = calcAverageWeights(unipartiteGraph, adjMat)
    timing.markEvent('2. Computed average weights.')

    # Size of connected component:
    cnctComponents = calcCnctComponents(unipartiteGraph)
    timing.markEvent('3. Computed connected components.')

    # Size of CNM community:
    communities = calcCommunities(idToCNM)
    timing.markEvent('4. Computed CNM communities.')

    # Pagerank:
    pageRanks = snap.TIntFltH()
    snap.GetPageRank(unipartiteGraph, pageRanks)
    timing.markEvent('5. Computed PageRank.')

    # combine the graph wide features with the existing surface features:
    for nid in features:
        #features[nid].append(avgWeights[nid])
        features[nid].append(cnctComponents[nid])
        features[nid].append(communities[nid])
        features[nid].append(pageRanks[nid])

    timing.finish()

    return features, componentFeatureFunc, CNMFeatureFunc

# Takes the graph and adjacency matrix, and uses these to update the
# features map for the unipartite graph.
# Returns the categorical feature function (from connected component ID to dummy feature vec).
# TODO: Improve this style.
def getUnipartiteSurfaceFeatures(graph, adjMat, features):

    # Cateogrical connected component labels:
    idToCC = labelConnectedComponents(graph)
    featureFunc1 = lambda x: 0.0 if x not in idToCC else idToCC[x]
    componentFeatureFunc = categorical.getCategoricalFeatureVec(featureFunc1, graph.Nodes())

    idToCNM = labelCNMCommunity(graph)
    featureFunc2 = lambda x: 0.0 if x not in idToCNM else idToCNM[x]
    CNMFeatureFunc = categorical.getCategoricalFeatureVec(featureFunc2, graph.Nodes())

    # idToCommunity = labelCommunities(graph)
    # featureFunc = lambda x: 0.0 if x not in idToCommunity else idToCommunity[x]
    # communityFeatureFunc = categorical.getCategoricalFeatureVec(featureFunc, graph.Nodes())

    for node in graph.Nodes():
        nid = node.GetId()

        # Node degree:
        features[nid].append(node.GetDeg())

        # Nodes at hop:
        # nodesAtHop = snap.TIntV()
        # features[nid].append(snap.GetNodesAtHop(graph, nid, 2, nodesAtHop, False))

        # Connected component category features:
        features[nid] += componentFeatureFunc(idToCC[nid]).tolist()

        # CNM community category features:
        features[nid] += CNMFeatureFunc(idToCNM[nid]).tolist()

    return componentFeatureFunc, CNMFeatureFunc, idToCNM #, communityFeatureFunc, idToCommunitiy

def calcAverageWeights(graph, adjMat):
    neighbors = defaultdict(list)
    # Get all the nodes that a node borders in the graph
    for edge in graph.Edges():
        nodeid1 = edge.GetSrcNId()
        nodeid2 = edge.GetDstNId()
        neighbors[nodeid1].append(nodeid2)
        neighbors[nodeid2].append(nodeid1)

    # Get the average weight per node connected to
    weights = {}
    for nodeid in neighbors:
        cols = neighbors[nodeid]
        weights[nodeid] = adjMat[nodeid, cols].sum() / float(len(cols))

    return weights

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


# Returns the sizes of the communities as a map from node id to size
def calcCommunities(idToCommunity):
    communityLens = defaultdict(int) # community ID to community size
    lenCommunities = {} # node ID to community size

    for nid in idToCommunity:
        communityLens[idToCommunity[nid]] += 1

    for nid in idToCommunity:
        lenCommunities[nid] = communityLens[idToCommunity[nid]]

    return lenCommunities

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
def defaultUnipartiteFeatures(componentFeatureFunc, CNMFeatureFunc): #, communityFeatureFunc):
    defaultFeatures = []
    defaultFeatures.append(0.0) # degree
    # defaultFeatures.append() # nodes at hop 2
    defaultFeatures += componentFeatureFunc(0).tolist() # connected component category
    defaultFeatures += CNMFeatureFunc(0).tolist() # CNM community category
    # defaultFeatures.append(0) # avg. weight of edges
    defaultFeatures.append(1.0) # size of connected component
    defaultFeatures.append(1.0) # size of CNM community
    # defaultFeatures.append(0.0) # clustering coefficient
    # defaultFeatures.append(0.0) # eigenvector value
    defaultFeatures.append(0.0) # pagerank score
    return defaultFeatures

# Creates a dictionary from node id to connected component index for a given graph.
def labelConnectedComponents(graph):

    components = {}
    CnCom = snap.TIntV()
    component = 1

    for node in graph.Nodes():
        nodeid = node.GetId()

        if nodeid in components:
            continue

        snap.GetNodeWcc(graph, nodeid, CnCom)
        if len(CnCom) == 1:
            components[nodeid] = 0.0
        else:
            for cnid in CnCom:
                components[cnid] = component
        component += 1

    return components

# Creates a dictionary from node id to community index for a given graph.
def labelCommunities(graph):

    communities = {}
    CmtyV = snap.TCnComV()
    snap.CommunityGirvanNewman(graph, CmtyV)

    community = 1
    for Cmty in CmtyV:
        for NI in Cmty:
            if Cmty.Len() == 1:
                communities[NI] = 0.0
            else:
                communities[NI] = community
        community += 1

    return communities

# Clauset-Newman-Moore community detection: returns dictionary form nide id to community index
def labelCNMCommunity(graph):

    communities = {}
    CmtyV = snap.TCnComV()
    modularity = snap.CommunityCNM(graph, CmtyV)
    # print "The modularity of the network is %f" % modularity

    communityIndex = 1
    for Cmty in CmtyV:
        for nid in Cmty:
            if Cmty.Len() == 1:
                communities[nid] = 0.0
            else:
                communities[nid] = communityIndex
        communityIndex += 1

    return communities

################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        year = int(arg)
        timing = Timer('creating unipartite graph for %d' % year)

        bipartiteGraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)
        unipartiteGraph = graph_funcs.loadGraph('Data/Unipartite-Graphs/%d.graph' % year, snap.TUNGraph)
        newToOldIDs = pickler.load('Data/Unipartite-NodeMappings/%d.newToOld' % year)
        timing.markEvent('Loaded input graphs/matrices.')

        for weightF in ['jaccard', 'affinity', 'jaccard2', 'cosine', 'adamic', 'weighted_adamic']:
            print '******* %s *******' % weightF
            adjMatrix = pickler.load('Data/Unipartite-Matrix/%d.%s' % (year, weightF))
            adjMatrix = adjMatrix.tocsc()

            features = generateFeatures(year, bipartiteGraph, unipartiteGraph, newToOldIDs, adjMatrix)
            pickler.save(features, 'Data/Features/%d%s.features' % (year, weightF))

            timing.markEvent('Processed %s weight function' % weightF)

        timing.finish()


## OUTDATED:::
# Features:

# 1. degree
# 2. nodes at hop 2
# 3. avg. weight of edges
# 4. size of connected component
# 5. size of community
# 6. categorical label of connected component
# 7. clustering coefficient
# 8. eigenvector value
# 9. pagerank score
