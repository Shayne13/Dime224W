#!/usr/bin/python

import sys, time, snap
import scipy.sparse as sp
from util import pickler
from collections import defaultdict
import numpy as np


def generateFeatures(year):
    
    print 'Beginning feature extraction for %d:' % year
    start = time.time()
    
    unipartiteGraph = snap.TUNGraph.Load(snap.TFIn('../Data/Unipartite-Graphs/%d.graph' % year))
    weightMatrix = pickler.load('../Data/Unipartite-Matrix/%d.jaccard' % year)
    weightMatrix = weightMatrix.tocsc()
    newToOldIDs = pickler.load('../Data/Unipartite-NodeMappings/%d.newToOld' % year)
    bipartiteGraph = snap.TNEANet.Load(snap.TFIn('../Data/Bipartite-Graphs/%d.graph' % year))
    print 'Finished loading input graphs/matrices. Time from start of cycle: %d' % (time.time() - start)
    
    bipartiteFeatures = extractBipartiteFeatures(bipartiteGraph)
    print 'Finished extracting bipartite features. Time from start of cycle: %d' % (time.time() - start)
    
    unipartiteFeatures = convertNewToOldIDs(extractUnipartiteFeatures(unipartiteGraph, weightMatrix), newToOldIDs)
    print 'Finished extracting unipartite features. Time from start of cycle: %d' % (time.time() - start)
    
    # append unipartite features to bipartite features for each node, returning combined feature dictionary:
    features = {}
    for oldNID in bipartiteGraph:
        features[oldNID] = bipartiteFeatures[oldNID] + unipartiteFeatures[oldNID]
    print 'Finished combining unipartite and bipartite features. Time from start of cycle: %d' % (time.time() - start)
    
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
        demRecipIDs = [rid for rid in cands[nid] if (bipartiteGraph.GetIntAttrDatN(rid, 'party') == 1) ]
        amountToDems = sum([ amounts[nid][rid] for rid in demRecipIDs ])
        features[nid].append(amountToDems / float(totalAmount[nid]))
    
    return features


def extractUnipartiteFeatures(unipartiteGraph, adjMat):
    start = time.time()
    
    features = defaultdict(list)
    getUnipartiteSurfaceFeatures(unipartiteGraph, adjMat, features)
    
    print 'Finished extracting surface features after: %d' % (time.time() - start)
    
    # Size of connected component:
    cnctComponents = calcCnctComponents(unipartiteGraph)
    
    print 'Finished computing connected components after: %d' % (time.time() - start)
    
    # Node clustering coefficients:
    NIdCCfH = snap.TIntFltH()
    snap.GetNodeClustCf(unipartiteGraph, NIdCCfH)
    
    print 'Finished computing clustering coefficients after: %d' % (time.time() - start)
    
    # Eigenvectors:
    eigenVal, eigenVecs = sp.linalg.eigs(adjMat, k=1)
    
    print 'Finished computing eigenvectors after: %d' % (time.time() - start)
    
    # Pagerank:
    pageRanks = snap.TIntFltH()
    snap.GetPageRank(unipartiteGraph, pageRanks)
    
    print 'Finished computing pagerank after: %d' % (time.time() - start)
    
    # combine the graph wide features with the existing surface features:
    for nid in features:
        features[nid].append(cnctComponents[nid])
        features[nid].append(NIdCCfH[nid])
        features[nid].append(eigenVecs[nid])
        features[nid].append(pageRanks[nid])
        
    print 'Finally finished aggregating features into one unipartite vector after: %d' % (time.time() - start)
        
    return features

# Takes the graph and adjacency matrix, and uses these to update the 
# features map for the unipartite graph.
def getUnipartiteSurfaceFeatures(graph, adjMat, features):
    
    for i, node in enumerate(graph.Nodes()):
        nid = node.GetId()
        
        # Node degree:
        features[nid].append(node.GetDeg())
        
        # Average weight of edges:
        avgWeight = (sum(adjMat[:,nid]) / np.sum([ 1.0 for j in adjMat[:,nid] if j > 0.0]))[0,0]
        features[nid].append(avgWeight)
        
        # Nodes at hop:
        nodesAtHop = snap.TIntV()
        #features[nid].append(snap.GetNodesAtHop(graph, nid, 2, nodesAtHop, False))


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

# Takes in the { unipartiteNodeIDs -> [ features ] } and newToOldID mapping
# and returns { bipartiteNodeIDs -> [ features ] }.
def convertNewToOldIDs(newIDFeatureMapping, newToOldIDs):
    oldIDFeatureMapping = {}
    
    for newID in newIDFeatureMapping:
        oldIDFeatureMapping[newToOldIDs[newID]] = newIDFeatureMapping[newID]
        
    return oldIDFeatureMapping


if __name__ == '__main__':
    for year in range(1980, 1990, 2):
		start = time.time()
		features = generateFeatures(year)
		pickler.save(features, '../Data/Features/%djaccard' % year + '.features')
		print 'Total time taken for this cycle: %d' % (time.time() - start)




