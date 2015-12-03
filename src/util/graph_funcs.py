import snap

################################################################################
# Miscellaneous helpful snap.py graph functions #
################################################################################

# Load a snap graph file from a filename (graph type defaults to snap.TNEANet
# but can be set by caller)
def loadGraph(filename, graphType = snap.TNEANet):
    return graphType.Load(snap.TFIn(filename))

# Save a snap graph to a file
def saveGraph(graph, filename):
    FOut = snap.TFOut(filename)
    graph.Save(FOut)
    FOut.Flush()

# Generator over all the recipient nodes in the graph
# If cfs is True we only return nodes with valid cfs scores (i.e. IsRecip == 1)
# If cfs is False we also return nodes without valid cfs scores (i.e. IsRecip ==
# 2).
# If full is True we only return full nodes with all their node attributes.
# If full is False we return all recipients, even stripped down ones.
def getRecipients(graph, cfs=False, full=False):
    for node in graph.Nodes():
        val = graph.GetIntAttrDatN(node.GetId(), 'IsRecip')
        if full and graph.GetIntAttrDatN(node.GetId(), 'IsFullNode') == 0: continue
        if val == 1:
            yield node
        elif cfs == False and val == 2:
            yield node

# Generator over all the donor nodes in the graph
# If full is True we only return full nodes with all their node attributes.
# If full is False we return all donor, even stripped down ones.
def getDonors(graph, full=False):
    for node in graph.Nodes():
        if full and graph.GetIntAttrDatN(node.GetId(), 'IsFullNode') == 0: continue
        if graph.GetIntAttrDatN(node.GetId(), 'IsRecip') == 0:
            yield node

# Generator over all the edges connected to this node id
def getEdgesWithNode(graph, nodeid):
    for edge in graph.Edges():
        if edge.GetSrcNId() == nodeid or edge.GetDstNId() == nodeid:
            yield edge

# Generator over all the edges connected to one of the node ids in this
# collection
def getEdgesWithNodeset(graph, nodeids):
    idSet = set(nodeids)
    for edge in graph.Edges():
        if edge.GetSrcNId() in idSet or edge.GetDstNId() in idSet:
            yield edge
