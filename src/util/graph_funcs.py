import snap

################################################################################
# Miscellaneous helpful snap.py graph functions #
################################################################################

# Load a snap graph file from a filename (graph type defaults to snap.TNEANet
# but can be set by caller)
def loadGraph(filename, graphType = snap.TNEANet):
    return graphType.Load(snap.TFIn(filename))

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
