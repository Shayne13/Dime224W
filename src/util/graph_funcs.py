import snap

################################################################################
# Miscellaneous helpful snap.py graph functions #
################################################################################

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

