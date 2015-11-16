import snap

# Given a node in a graph, extract all the node attributes into a feature vector
# represented by a dictionary/Javascript style object
def getNodeFeatures(graph, node):
    # The snap vectors that will house the raw data
    intVals = snap.TIntV()
    intNames = snap.TStrV()
    fltVals = snap.TFltV()
    fltNames = snap.TStrV()
    strVals = snap.TStrV()
    strNames = snap.TStrV()
    
    # Load the raw data from the node
    graph.IntAttrValueNI(node, intVals)
    graph.IntAttrNameNI(node, intNames)
    graph.FltAttrValueNI(node, fltVals)
    graph.FltAttrNameNI(node, fltNames)
    graph.StrAttrValueNI(node, strVals)
    graph.StrAttrNameNI(node, strNames)
    
    # Put the data into a dictionary to be returned
    return _aggregate_vecs(intNames, intVals, fltNames, fltVals, strNames, strVals)

# Given an edge in a graph, extract all the node attributes into a feature vector
# represented by a dictionary/Javascript style object
def getEdgeFeatures(graph, edge):
    # The snap vectors that will house the raw data
    intVals = snap.TIntV()
    intNames = snap.TStrV()
    fltVals = snap.TFltV()
    fltNames = snap.TStrV()
    strVals = snap.TStrV()
    strNames = snap.TStrV()
    
    # Load the raw data from the edge
    graph.IntAttrValueEI(edge, intVals)
    graph.IntAttrNameEI(edge, intNames)
    graph.FltAttrValueEI(edge, fltVals)
    graph.FltAttrNameEI(edge, fltNames)
    graph.StrAttrValueEI(edge, strVals)
    graph.StrAttrNameEI(edge, strNames)
    
    # Put the data into a dictionary to be returned
    return _aggregate_vecs(intNames, intVals, fltNames, fltVals, strNames, strVals)

# Aggregate the int, float, and string attributes into a single dict
def _aggregate_vecs(intNames, intVals, fltNames, fltVals, strNames, strVals):
    vec = {}
    for i in range(intNames.Len()):
        vec[intNames[i]] = intVals[i]
        
    for i in range(fltNames.Len()):
        vec[fltNames[i]] = fltVals[i]
        
    for i in range(strNames.Len()):
        vec[strNames[i]] = strVals[i]
        
    return vec
