#!/usr/bin/python
# Module: donor_relationships
# To call from the command line, run `python src/donor_relationships <years>`, where
# <years> contains each year whose graph you want to generate.

import snap, math, sys
from collections import defaultdict
from util import pickler, graph_funcs
from util.Timer import Timer
import scipy.sparse as sp

# Given an election cycle and a weighting function, creates a unipartite
# donor-donor graph. The weighting function is described further down in this file.
def createDonorDonorGraph(year, weightF):
    timing = Timer('creating donor-donor graph for %d' % year)

    # Load the old bipartite graph graph
    bipartiteGraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)

    # Load the info about each donor and their recipients
    numDonations, totalAmount, cands, transactions, amounts = getDonorInfos(bipartiteGraph)
    timing.markEvent('Got info about donor nodes')

    # Create initial unipartite graph with just nodes and node attributes
    unipartiteGraph, oldToNew, newToOld = cloneBipartiteNodes(bipartiteGraph, cands)
    timing.markEvent('Finished cloning nodes')

    jaccardData = []
    jaccard2Data = []
    affinityData = []
    cosineData = []
    r = []
    c = []

    # Add the weighted edges for every relevant pair of donor nodes
    nodesDone = 0

    for i, newID1 in enumerate(newToOld.keys()):
        oldID1 = newToOld[newID1]
        for newID2 in newToOld.keys()[i + 1:]:
            oldID2 = newToOld[newID2]

            sharedCands = cands[oldID1].intersection(cands[oldID2])
            if not sharedCands: continue

            # Calculate the weight
            weights = weightF(
                oldID1,
                oldID2,
                sharedCands,
                numDonations,
                totalAmount,
                cands,
                transactions,
                amounts
            )

            r.append(newID1)
            r.append(newID2)
            c.append(newID2)
            c.append(newID1)
            jaccardData.append(weights['jaccard'])
            jaccardData.append(weights['jaccard'])
            jaccard2Data.append(weights['jaccard2'])
            jaccard2Data.append(weights['jaccard2'])
            affinityData.append(weights['affinity'])
            affinityData.append(weights['affinity'])
            cosineData.append(weights['cosine'])
            cosineData.append(weights['cosine'])

            # Add the edges between the two nodes and their weights
            unipartiteGraph.AddEdge(newID1, newID2)

        nodesDone += 1
        if nodesDone % 100 == 0:
            timing.markEvent('Finished %d outer loops out of %d' % \
                    (nodesDone, unipartiteGraph.GetNodes()))

    N = len(newToOld)
    jaccardAdjMat = sp.csr_matrix((jaccardData, (r, c)), shape = (N, N))
    jaccard2AdjMat = sp.csr_matrix((jaccard2Data, (r, c)), shape = (N, N))
    affinityAdjMat = sp.csr_matrix((affinityData, (r, c)), shape = (N, N))
    cosineAdjMat = sp.csr_matrix((cosineData, (r, c)), shape = (N, N))

    timing.finish()
    return unipartiteGraph, jaccardAdjMat, jaccard2AdjMat, affinityAdjMat, cosineAdjMat, newToOld, oldToNew

# Takes in the bipartite graph and generates the initial unipartiteGraph with just nodes
# and node attributes.
def cloneBipartiteNodes(bipartiteGraph, cands, threshold = 2):
    # Create the new donor-donor graph
    unipartiteGraph = snap.TUNGraph.New()
    oldToNew = {}
    newToOld = {}

    # Add each donor node from the old graph to the new one
    for node in graph_funcs.getDonors(bipartiteGraph):
        oldID = node.GetId()
        if len(cands[oldID]) <= threshold:
            continue

        newID = unipartiteGraph.AddNode()
        oldToNew[oldID] = newID
        newToOld[newID] = oldID

    return unipartiteGraph, oldToNew, newToOld

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

# ----- WEIGHTING FUNCTIONS -----

# The weighting function must take in the 2 cnodeids, their shared candidates
# and the following 5 dictionary parameters, each from cnodeid to:
# 1. The total number of donations that donor made
# 2. The total amount that donor donated
# 3. The set of rnodeids that donor gave to
# 4. A dictionary showing how many donations the donor made to each rnodeid
# 5. A dictionary showing how much the donor gave to each rnodeid

def getWeightScores(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts):
    weights = {}

    n1, s1 = jaccardSimilarity(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts)
    n2, s2 = jaccardSimilarity2(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts)
    n3, s3 = affinity(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts)
    n4, s4 = cosSim(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts)

    weights[n1] = s1
    weights[n2] = s2
    weights[n3] = s3
    weights[n4] = s4

    return weights

# Simple Jaccard Similarity
def jaccardSimilarity(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts):
    score = float(len(sharedCands)) / len(cands[id1].union(cands[id2]))
    return 'jaccard', score

# Jaccard Similarity using the intersection of the fraction of total wealth donated to the same candidates:
def jaccardSimilarity2(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts):
    donationIntersectionAmount = sum([min(amounts[id1][cand], amounts[id2][cand]) for cand in sharedCands])
    denom = (totalAmount[id1] + totalAmount[id2])
    # if (denom == 0):
    #     return 'jaccard2', 0.0
    return 'jaccard2', float(donationIntersectionAmount) / denom

# See: https://stats.stackexchange.com/questions/142132/is-this-a-valid-method-for-unipartite-projection-of-a-bipartite-graph
def affinity(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts):
    score = ((len(sharedCands) * len(cands)) / (len(cands[id1]) + len(cands[id2]))) / 1.0
    return 'affinity', score

# Cosine Similarity:
def cosSim(id1, id2, sharedCands, numDonations, totalAmount, cands, transactions, amounts):
    numerator = sum([amounts[id1][cand] * amounts[id2][cand] for cand in sharedCands])
    denomA = math.sqrt(sum([amounts[id1][cand] ** 2 for cand in sharedCands]))
    denomB = math.sqrt(sum([amounts[id2][cand] ** 2 for cand in sharedCands]))
    score = numerator / (float(denomA) * denomB)
    return 'cosine', score


################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    overallTiming = Timer('all unipartite graphs')
    for arg in sys.argv[1:]:
        year = int(arg)
        timing = Timer('Creating unipartite graph for %d' % year)

        graph, wmat1, wmat2, wmat3, wmat4, newToOld, oldToNew = createDonorDonorGraph(year, getWeightScores)

        # Save the SNAP graph:
        outfile = 'Data/Unipartite-Graphs/%d.graph' % year
        graph_funcs.saveGraph(graph, outfile)

        # Save the weight matrices:
        matrixPrefix = 'Data/Unipartite-Matrix/%d' % year
        pickler.save(wmat1, matrixPrefix + '.jaccard')
        pickler.save(wmat2, matrixPrefix + '.jaccard2')
        pickler.save(wmat3, matrixPrefix + '.affinity')
        pickler.save(wmat4, matrixPrefix + '.cosine')

        # Save the bipartite-unipartite corresponding node ID dictionaries:
        mappingPrefix = 'Data/Unipartite-NodeMappings/%d' % year
        pickler.save(newToOld, mappingPrefix + '.newToOld')
        pickler.save(oldToNew, mappingPrefix + '.oldToNew')

        timing.finish()

    overallTiming.finish()


# ------ OLD CODE: ------

            # weight = weightF(
            #     len(sharedCands),
            #     sharedTransactions,
            #     sharedAmount,
            #     len(cands[id1].union(cands[id2])),
            #     numDonations[id1] + numDonations[id2],
            #     totalAmount[id1] + totalAmount[id2],
            # )

            # Get the number of transactions and the total amount given to shared
            # candidates
            # sharedTransactions = sharedAmount = 0
            # for cand in sharedCands:
            #     sharedTransactions += transactions[id1][cand] + transactions[id2][cand]
            #     sharedAmount += amounts[id1][cand] + amounts[id2][cand]
