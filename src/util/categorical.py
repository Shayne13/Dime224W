import snap, graph_funcs
import numpy as np

# Function: getCategoricalFeatureVec
# Params: graph as snap.TNEANet graph
#         featureFunc as function from int (node id in bipartite graph) to
#                        category (either int or string)
#         iteratorFunc: pass in graph_funcs.getDonors or graph_funcs.getRecipients or 
#                        graph_funcs.getAllNodeIDs
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from category (either int or string) to a numpy vector
# ----------------------------------
# Creates a function that produces a feature vector based on a particular
# categorical attribute. This is done using dummy variables for all but one of
# the values that the string attribute can take.
def getCategoricalFeatureVec(featureFunc, iterator):
    categories = {}
    # iteratorFunc = graph_funcs.getRecipients if isRecip else graph_funcs.getDonors

    for node in iterator:
        val = featureFunc(node.GetId())
        if val not in categories: categories[val] = len(categories)

    def getFeatures(cat):
        features = np.zeros(len(categories) - 1)
        index = categories[cat]
        if index < len(features): features[index] = 1
        return features

    return getFeatures

# Function: getIntAttrFeatureVec
# Params: graph as snap.TNEANet graph
#         attr as as string indicating int node attribute name
#         isRecip: optional bool indicating whether to iterate over recipients
#                  (default) or donors
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from category (either int or string) to a numpy vector
# ------------------------------
# Convenience wrapper around getCategoricalFeatureVec for the common case of
# a categorical int node attribute in the bipartite graph.
def getIntAttrFeatureVec(graph, attr, isRecip=True, full=False):
    featureFunc = lambda nodeid: graph.GetIntAttrDatN(nodeid, attr)
    coreIteratorFunc = graph_funcs.getRecipients(graph) if isRecip else graph_funcs.getDonors
    return getCategoricalFeatureVec(graph, featureFunc, isRecip, full)

# Function: getStrAttrFeatureVec
# Params: graph as snap.TNEANet graph
#         attr as as string indicating string node attribute name
#         isRecip: optional bool indicating whether to iterate over recipients
#                  (default) or donors
#         full: optional bool indicating whether to iterate over all donor/
#               recipient nodes (default) or only full nodes.
# Returns: function from category (either int or string) to a numpy vector
# ------------------------------
# Convenience wrapper around getCategoricalFeatureVec for the common case of
# a categorical string node attribute in the bipartite graph.
def getStrAttrFeatureVec(graph, attr, isRecip=True, full=False):
    featureFunc = lambda nodeid: graph.GetStrAttrDatN(nodeid, attr)
    return getCategoricalFeatureVec(graph, featureFunc, isRecip, full)
