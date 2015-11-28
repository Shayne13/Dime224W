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
    graph.save(FOut)
    FOut.Flush()

# Generator over all the recipient nodes in the graph
def getRecipients(graph):
    for node in graph.Nodes():
        if graph.GetIntAttrDatN(node.GetId(), 'IsRecip') == 1:
            yield node

# Generator over all the donor nodes in the graph
def getDonors(graph):
    for node in graph.Nodes():
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

