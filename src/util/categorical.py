import snap, graph_funcs
import numpy as np

# Function: getCategoricalFeatureVec
# Params: graph as snap.TNEANet graph
#         featureFunc as function from int (node id in bipartite graph) to
#                        category (either int or string)
#         isRecip: optional bool indicating whether to iterate over recipients
#                  (default) or donors
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from TNEANet node to a numpy vector
# ----------------------------------
# Creates a function that produces a feature vector based on a particular
# categorical attribute. This is done using dummy variables for all but one of
# the values that the string attribute can take.
def getCategoricalFeatureVec(graph, featureFunc, isRecip=True, full=False):
    categories = {}
    iteratorFunc = graph_funcs.getRecipients if isRecip else graph_funcs.getDonors

    for node in iteratorFunc(graph, full=full):
        val = featureFunc(node.GetId())
        if val not in categories: categories[val] = len(categories)

    def getFeatures(node):
        features = np.zeros(len(categories) - 1)
        index = categories[featureFunc(node.GetId())]
        if index < len(features): features[index] = 1
        return features

    return getFeatures

# Function: getFeatureVecForIntAttr
# Params: graph as snap.TNEANet graph
#         attr as as string indicating int node attribute name
#         isRecip: optional bool indicating whether to iterate over recipients
#                  (default) or donors
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from TNEANet node to a numpy vector
# ---------------------------------
# Convenience wrapper around getCategoricalFeatureVec for the common case of
# a categorical int node attribute in the bipartite graph.
def getFeatureVecForIntAttr(graph, attr, isRecip=True, full=False):
    featureFunc = lambda nodeid: graph.GetIntAttrDatN(nodeid, attr)
    return getCategoricalFeatureVec(graph, featureFunc, isRecip, full)

# Function: getFeatureVecForStrAttr
# Params: graph as snap.TNEANet graph
#         attr as as string indicating string node attribute name
#         isRecip: optional bool indicating whether to iterate over recipients
#                  (default) or donors
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from TNEANet node to a numpy vector
# ---------------------------------
# Convenience wrapper around getCategoricalFeatureVec for the common case of
# a categorical string node attribute in the bipartite graph.
def getFeatureVecForStrAttr(graph, attr, isRecip=True, full=False):
    featureFunc = lambda nodeid: graph.GetStrAttrDatN(nodeid, attr)
    return getCategoricalFeatureVec(graph, featureFunc, isRecip, full)
