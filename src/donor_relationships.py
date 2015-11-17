import snap, time
from collections import defaultdict

# Given an election cycle and a weighting function, creates a unipartite
# donor-donor graph. The weighting function must take in the following
# parameters, all numbers:
# 1. The number of candidates the two donors have in common
# 2. The number of donations the two donors made to shared candidates
# 3. The total amount the two donors donated to shared candidates
# 4. The total number of candidates the two donors donated to
# 5. The total number of donations the two donors made
# 6. The total amount the two donors donated
def createDonorDonorGraph(year, weightF):
    print 'Creating donor-donor graph for %d' % year
    start = time.time()

    # Load the old bipartite graph graph
    bipartiteGraph = snap.TNEANet.Load(snap.TFIn('Data/Bipartite-Graphs/%d.graph' % year))

    # Create the new donor-donor graph
    unipartiteGraph = snap.TNEANet.New()

    # Load the info about each donor and their recipients
    numDonations, totalAmount, cands, transactions, amounts = \
        getDonorInfos(bipartiteGraph)
    print 'Got info about donor nodes'
    print 'Current time elapsed: %f' % (time.time() - start)


    # Add each donor node from the old graph to the new one
    for node in bipartiteGraph.Nodes():
        if bipartiteGraph.GetIntAttrDatN(node.GetId(), 'IsRecip') == 1:
            continue
        cloneNode(bipartiteGraph, unipartiteGraph, node.GetId())

    print 'Finished cloning nodes'
    print 'Current time elapsed: %f' % (time.time() - start)

    # Add the weighted edges for every relevant pair of donor nodes
    nodesDone = 0
    for node1 in unipartiteGraph.Nodes():
        id1 = node1.GetId()
        for node2 in unipartiteGraph.Nodes():
            id2 = node2.GetId()
            if id1 >= id2:
                continue

            # Get the set of all the candidates both donors donated to, and
            # move on if they have none in common
            sharedCands = cands[id1].intersection(cands[id2])
            if not sharedCands:
                continue

            # Get the number of transactions and the total amount given to shared
            # candidates
            sharedTransactions = sharedAmount = 0
            for cand in sharedCands:
                sharedTransactions += transactions[id1][cand] + transactions[id2][cand]
                sharedAmount += amounts[id1][cand] + amounts[id2][cand]

            # Calculate the weight
            weight = weightF(
                len(sharedCands),
                sharedTransactions,
                sharedAmount,
                len(cands[id1].union(cands[id2])),
                numDonations[id1] + numDonations[id2],
                totalAmount[id1] + totalAmount[id2]
            )

            # Add the edges between the two nodes and their weights
            e1 = unipartiteGraph.AddEdge(id1, id2)
            e2 = unipartiteGraph.AddEdge(id2, id1)
            unipartiteGraph.AddFltAttrDatE(e1, weight, 'weight')
            unipartiteGraph.AddFltAttrDatE(e2, weight, 'weight')
        nodesDone += 1
        if nodesDone % 100 == 0:
            print 'Finished %d outer loops out of %d' % (nodesDone, unipartiteGraph.GetNodes())
            print 'Current time elapsed: %f' % (time.time() - start)

    print 'Total time taken: %f' % (time.time() - start)

    return unipartiteGraph


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

# Clones a particular node from one graph to another, keeping the original
# node id and attributes but discarding all of the edges
def cloneNode(graph1, graph2, nodeid):
    graph2.AddNode(nodeid)

    # Copy the attributes and names from the original node
    intNames = snap.TStrV()
    fltNames = snap.TStrV()
    strNames = snap.TStrV()
    intVals = snap.TIntV()
    fltVals = snap.TFltV()
    strVals = snap.TStrV()

    graph1.IntAttrNameNI(nodeid, intNames)
    graph1.FltAttrNameNI(nodeid, fltNames)
    graph1.StrAttrNameNI(nodeid, strNames)
    graph1.IntAttrValueNI(nodeid, intVals)
    graph1.FltAttrValueNI(nodeid, fltVals)
    graph1.StrAttrValueNI(nodeid, strVals)

    # Add each of the attributes to the new node by type
    for i in range(intNames.Len()):
        graph2.AddIntAttrDatN(nodeid, intVals[i], intNames[i])
    for i in range(fltNames.Len()):
        graph2.AddFltAttrDatN(nodeid, fltVals[i], fltNames[i])
    for i in range(strNames.Len()):
        graph2.AddStrAttrDatN(nodeid, strVals[i], strNames[i])
