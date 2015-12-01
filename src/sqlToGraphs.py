#!/usr/bin/python
# Module: sqlToGraph
# To call from the command line, run `python src/sqlToGraph <years>`, where
# <years> contains each year whose graph you want to generate.

import snap, sys
import sqlite3 as lite
from util import pickler, graph_funcs
from util.Timer import Timer
from collections import defaultdict

################################################################################
# Module functions #
################################################################################

# Given a year, creates a bipartite graph for that year and saves that graph,
# along with maps from SQL primary keys to node/edge ids.
def createAndSaveGraph(year):
    G = snap.TNEANet.New()

    # Open the SQL connection and fill in the nodes and edges
    infile = 'Data/DBs/%d.db' % year
    con = lite.connect(infile)
    with con:
        cur = con.cursor()
        contribMapping = getRelevantDonors(G, cur)
        recipMapping = getRelevantRecipients(G, cur)
        edgeMapping = getRelevantTransactions(G, cur, contribMapping, recipMapping)

    # Save the graph to a file in Data/Bipartite-Graphs
    outfile = 'Data/Bipartite-Graphs/%d.graph' % year
    graph_funcs.saveGraph(G, outfile)

    # Save the edge, contributor, and recipient mappings to files in Data/Mappings
    mapPrefix = 'Data/Mappings/%d' % year
    pickler.save(contribMapping, mapPrefix + '.contribs')
    pickler.save(recipMapping, mapPrefix + '.recips')
    pickler.save(edgeMapping, mapPrefix + '.edges')

# Gets the relevant donor (i.e. all those who had net positive donations this
# cycle), adds them to the graph, and when possible, adds detailed information
# about them from the Contributors table. Returns a mapping from cids to
# cnodeids.
def getRelevantDonors(graph, cur):
    # Initialize a map from cids to cnodeids.
    contributorMapping = {}

    # Query the DB for the cids for all donors with positive net donations
    # during this cycle and add their nodes to the network.
    getCidsQuery = 'SELECT DISTINCT cid FROM Transactions WHERE amount > 0'
    cur.execute(getCidsQuery)
    cidRows = cur.fetchall()
    for row in cidRows:
        cid = row[0]
        cnodeid = graph.AddNode()
        graph.AddIntAttrDatN(cnodeid, 0, 'IsRecip')
        graph.AddIntAttrDatN(cnodeid, 0, 'IsFullNode')
        contributorMapping[cid] = cnodeid

    # Get detailed info about each donor in the Contributors table and update
    # the node attributes accordingly
    getContributorInfo = 'SELECT * FROM Contributors'
    cur.execute(getContributorInfo)
    donors = cur.fetchall()
    for donor in donors:
        # Skip over donors that weren't in the set of cids
        cid = donor[contributorIndices['cid']]
        if cid not in contributorMapping: continue

        # Get the node id for this cid
        cnodeid = contributorMapping[cid]

        # Mark this node as full since we have Contributors table data about it
        graph.AddIntAttrDatN(cnodeid, 1, 'IsFullNode')

        # Add each node attribute to the node accordingly
        for attribute, index in contributorIndices.iteritems():
            val = donor[index]
            addNodeAttrib(graph, cnodeid, val, attribute)

    return contributorMapping

# Gets the relevant recipients (i.e. all those who had positive receipts this
# cycle), adds them to the graph, and when possible, adds detailed information
# about them from the Recipients table. Returns a mapping from years to rids to
# seats to rnodeids.
def getRelevantRecipients(graph, cur):
    # Initialize a map from years to rids to seats to rnodeids. The defaultdict
    # wrapping allows rnodeids to be inserted easily without having to check
    # every single index.
    recipientMapping = defaultdict(defaultDictOfDicts)

    # Query the DB for the rids, years, and seats for all recipients with
    # positive receipts during this cycle and add their nodes to the network.
    getRidsQuery = 'SELECT rid, year, seat, cfs FROM Transactions GROUP BY rid, year, seat HAVING MAX(amount) > 0'
    cur.execute(getRidsQuery)
    ridRows = cur.fetchall()
    for row in ridRows:
        rid, year, seat, cfs = row[0], row[1], row[2], row[3]
        rnodeid = graph.AddNode()
        recipientMapping[year][rid][seat] = rnodeid
        if (cfs == None):
            graph.AddIntAttrDatN(rnodeid, 2, 'IsRecip')
        else:
            graph.AddIntAttrDatN(rnodeid, 1, 'IsRecip')
        graph.AddIntAttrDatN(rnodeid, 0, 'IsFullNode')

    # Get detailed info about each recipient in the Recipients table and update
    # the node attributes accordingly
    getRecipientInfo = 'SELECT * FROM Recipients'
    cur.execute(getRecipientInfo)
    recipients = cur.fetchall()
    for rec in recipients:
        # If this recipient didn't have net receipts this cycle, skip them
        year = rec[recipientIndices['year']]
        rid = rec[recipientIndices['rid']]
        seat = rec[recipientIndices['seat']]
        if seat not in recipientMapping[year][rid]: continue

        # Get the node id for this cid
        rnodeid = recipientMapping[year][rid][seat]

        # Mark this node as full since we have Recipients table data about it
        graph.AddIntAttrDatN(rnodeid, 1, 'IsFullNode')

        # Add each node attribute to the node accordingly
        for attribute, index in recipientIndices.iteritems():
            val = rec[index]
            addNodeAttrib(graph, rnodeid, val, attribute)

    # Return a mapping from db primary keys (year/rid/seat) to node IDs
    return recipientMapping

# Gets the relevant relevant (i.e. all those whose donor and recipient are both
# relevant), adds them  as edges to the graph, and adds detailed information
# about them from the Transactions table. Returns a mapping from years to tids
# to seats to edge ids.
def getRelevantTransactions(graph, cur, contribMapping, recipientMapping):
    # Initialize a map from years to tids to edge ids. The defaultdict wrapping
    # allows edge ids to be inserted easily without having to check every single
    # index.
    edgeMapping = defaultdict(dict)

    # Query the DB for all the transactions in this cycle
    query = 'SELECT * FROM Transactions'
    cur.execute(query)
    transactions = cur.fetchall()
    for transaction in transactions:
        # Get the info needed to identify the source and destination of the edge
        year = transaction[transactionIndices['year']]
        tid = transaction[transactionIndices['tid']]
        cid = transaction[transactionIndices['cid']]
        rid = transaction[transactionIndices['rid']]
        seat = transaction[transactionIndices['seat']]
        amount = transaction[transactionIndices['amount']]

        # If the amount is negative or 0, we don't care; skip it.
        if amount <= 0: continue

        # If the cid doesn't have a node, it's irrelevant; skip it.
        if cid not in contribMapping: continue
        cnodeid = contribMapping[cid]

        # If the contributor node is stripped down, add auxiliary info about it
        # from the Transactions table
        if graph.GetIntAttrDatN(cnodeid, 'IsFullNode') == 0:
            addContributorFromTransaction(graph, transaction, cnodeid)

        # If the year-rid-seat tuple doesn't have a node, it's irrelevant; skip it.
        if seat not in recipientMapping[year][rid]: continue
        rnodeid = recipientMapping[year][rid][seat]

        # If the recipient node is stripped down, add auxiliary info about it
        # from the Transactions table
        if graph.GetIntAttrDatN(rnodeid, 'IsFullNode') == 0:
            addRecipientFromTransaction(graph, transaction, rnodeid)

        edgeID = graph.AddEdge(cnodeid, rnodeid)

        # Add a mapping from the year/tid to the edge ID
        edgeMapping[year][tid] = edgeID

        # Add each edge attribute to the edge accordingly
        for attrib, index in transactionIndices.iteritems():
            val = transaction[index]
            addEdgeAttrib(graph, edgeID, val, attrib)

    return edgeMapping

# Add the info for a stripped-down contributor node usng info from a transaction
def addContributorFromTransaction(graph, transaction, cnodeid):
    for attrib in set(transactionIndices).intersection(set(contributorIndices)):
        val = transaction[transactionIndices[attrib]]
        addNodeAttrib(graph, cnodeid, val, attrib)

# Add the info for a stripped-down recipient node usng info from a transaction
def addRecipientFromTransaction(graph, transaction, rnodeid):
    for attrib in set(transactionIndices).intersection(set(recipientIndices)):
        val = transaction[transactionIndices[attrib]]
        addNodeAttrib(graph, rnodeid, val, attrib)

# Add a node attribute. Handles the typechecking automatically.
def addNodeAttrib(graph, nodeID, val, attrib):
    if not val: return

    if attrib in intAttribsNode:
        graph.AddIntAttrDatN(nodeID, val, attrib)
    elif attrib in stringAttribsNode:
        graph.AddStrAttrDatN(nodeID, val, attrib)
    elif attrib in floatAttribsNode:
        graph.AddFltAttrDatN(nodeID, val, attrib)
    else:
        raise NameError('Unknown node attribute ' + attrib)

# Add an edge attribute. Handles the typechecking automatically
def addEdgeAttrib(graph, edgeID, val, attrib):
    if not val: return

    # Don't duplicate node attributes
    if attrib in intAttribsNode \
            or attrib in stringAttribsNode \
            or attrib in floatAttribsNode:
        return

    if attrib in intAttribsEdge:
        graph.AddIntAttrDatE(edgeID, val, attrib)
    elif attrib in stringAttribsEdge:
        graph.AddStrAttrDatE(edgeID, val, attrib)
    elif attrib in floatAttribsEdge:
        graph.AddFltAttrDatE(edgeID, val, attrib)
    else:
        raise NameError('Unknown edge attribute ' + attrib)

# A function to return a default dict of dicts. Necessary to pickle the
# recipientMapping defaultdict.
def defaultDictOfDicts():
    return defaultdict(dict)

################################################################################
# Module constants #
################################################################################

# Define the node attributes (the columns of the Recipients and Contributors tables)
intAttribsNode = set([
    'year', 'party', 'incumb', 'numgivers', 'gender', 'didprimary', 'winner',
    'candstatus', 'fecyear', 'candorcomm', 'cid', 'indiv'
])
floatAttribsNode = set([
    'cfs', 'cfsdyn', 'partisanship', 'indistrict', 'instate', 'cfscore'
])
stringAttribsNode = set(['rid', 'seat', 'district', 'state'])

# Define the edge attributes (the columns of the Transactions table)
intAttribsEdge = set(['year', 'amount', 'cid', 'indiv', 'party', 'candorcomm'])
floatAttribsEdge = set(['cfscore', 'cfs'])
stringAttribsEdge = set(['tid', 'ttid', 'date', 'rid', 'district', 'seat'])

# Mappings from column name to index for each of the three tables
recipientIndices = {
    'year': 0,
    'rid': 1,
    'cid': 2,
    'party': 3,
    'seat': 4,
    'district': 5,
    'incumb': 6,
    'cfs': 7,
    'cfsdyn': 8,
    'numgivers': 9,
    'gender': 10,
    'didprimary': 11,
    'winner': 12,
    'partisanship': 13,
    'indistrict': 14,
    'instate': 15,
    'candstatus': 16,
    'fecyear': 17,
    'candorcomm': 18,
}
contributorIndices ={'cid': 0, 'indiv': 1, 'state': 2, 'cfscore': 3}
transactionIndices = {
    'year': 0,
    'tid': 1,
    'ttid': 2,
    'amount': 3,
    'date': 4,
    'cid': 5,
    'indiv': 6,
    'rid': 7,
    'party': 8,
    'candorcomm': 9,
    'district': 10,
    'seat': 11,
    'cfscore': 12,
    'cfs': 13,
}

################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    for arg in sys.argv[1:]:
        year = int(arg)
        timing = Timer('graph for %d' % year)
        createAndSaveGraph(year)
        timing.finish()
