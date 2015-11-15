#!/usr/bin/python

import snap, time, sys
import sqlite3 as lite
from util import pickler

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
    'party': 2,
    'seat': 3,
    'district': 4,
    'incumb': 5,
    'cfs': 6,
    'cfsdyn': 7,
    'numgivers': 8,
    'gender': 9,
    'didprimary': 10,
    'winner': 11,
    'partisanship': 12,
    'indistrict': 13,
    'instate': 14,
    'candstatus': 15,
    'fecyear': 16,
    'candorcomm': 17,
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

# Add a node attribute--handles the typechecking automatically
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

# Add an edge attribute--handles the typechecking automatically
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

def getRelevantDonors(graph, cur):
    # Query the DB for all the donors with transactions during this cycle
    query = '''
        SELECT *
        FROM Contributors
        WHERE cid IN (
            SELECT cid FROM Transactions
        )
    '''
    cur.execute(query)
    donors = cur.fetchall()

    contributorMapping = {}

    for donor in donors:
        # Add the contributor node to the graph and note that it is not a recipient
        cid = donor[contributorIndices['cid']]
        cnodeid = graph.AddNode()
        graph.AddIntAttrDatN(cnodeid, 0, 'IsRecip')
        graph.AddIntAttrDatN(cnodeid, 1, 'IsFullNode')

        contributorMapping[cid] = cnodeid

        # Add each node attribute to the node accordingly
        for attribute, index in contributorIndices.iteritems():
            val = donor[index]
            addNodeAttrib(graph, cnodeid, val, attribute)

    return contributorMapping

def getRelevantRecipients(graph, cur):
    # Query the DB for all the recipients with transactions during this cycle
    query = '''
        SELECT r.rid, r.year, r.party, r.seat, r.district, r.incumb, r.cfs,
               r.cfsdyn, r.numgivers, r.gender, r.didprimary, r.winner,
               r.partisanship, r.indistrict, r.instate, r.candstatus, r.fecyear,
               r.candorcomm
        FROM Recipients r
        JOIN Transactions t
        WHERE r.rid = t.rid AND r.year = t.year AND r.seat = t.seat
    '''
    cur.execute(query)
    recipients = cur.fetchall()

    recipientMapping = {}
    for rec in recipients:
        # Add this node and note that it is a recipient
        rnodeid = graph.AddNode()
        graph.AddIntAttrDatN(rnodeid, 1, 'IsRecip')
        graph.AddIntAttrDatN(rnodeid, 1, 'IsFullNode')

        # Add a mapping from the year/rid/seat primary key to the rnodeid
        year = rec[recipientIndices['year']]
        rid = rec[recipientIndices['rid']]
        seat = rec[recipientIndices['seat']]
        if year not in recipientMapping:
            recipientMapping[year] = {}
        if rid not in recipientMapping[year]:
            recipientMapping[year][rid] = {}
        recipientMapping[year][rid][seat] = rnodeid

        # Add each node attribute to the node accordingly
        for attribute, index in recipientIndices.iteritems():
            val = rec[index]
            addNodeAttrib(graph, rnodeid, val, attribute)

    # Return a mapping from db primary keys (year/rid/seat) to node IDs
    return recipientMapping

# Add a new, stripped-down contributor node usng info from a trnasaction
def addContributorFromTransaction(graph, transaction):
    cnodeid = graph.AddNode()
    graph.AddIntAttrDatN(cnodeid, 'IsRecip', 0)
    graph.AddIntAttrDatN(cnodeid, 0, 'IsFullNode')

    for attrib in set(transactionIndices).intersection(set(contributorIndices)):
        val = transaction[transactionIndices[attrib]]
        addNodeAttrib(graph, cnodeid, val, attrib)

    return cnodeid

# Add a new, stripped-down recipient node usng info from a trnasaction
def addRecipientFromTransaction(graph, transaction):
    rnodeid = graph.AddNode()
    graph.AddIntAttrDatN(rnodeid, 'IsRecip', 1)
    graph.AddIntAttrDatN(rnodeid, 0, 'IsFullNode')

    for attrib in set(transactionIndices).intersection(set(recipientIndices)):
        val = transaction[transactionIndices[attrib]]
        addNodeAttrib(graph, rnodeid, val, attrib)

    return rnodeid

def getRelevantTransactions(graph, cur, contribMapping, recipientMapping):
    # Query the DB for all the transactions in this cycle
    query = 'SELECT * FROM Transactions'
    cur.execute(query)
    transactions = cur.fetchall()
    edgeMapping = {}

    for transaction in transactions:
        # Get the info needed to identify the source and destination of the edge
        year = transaction[transactionIndices['year']]
        tid = transaction[transactionIndices['tid']]
        cid = transaction[transactionIndices['cid']]
        rid = transaction[transactionIndices['rid']]
        seat = transaction[transactionIndices['seat']]

        # If the cid didn't appear in the Contributors table, add a
        # stripped down version of its node to the graph
        if cid not in contribMapping:
            contribMapping[cid] = \
                addContributorFromTransaction(graph, transaction)
        cnodeid = contribMapping[cid]

        # If the year/rid/seat didn't appear in the Recipients table, add a
        # stripped down version of its node to the graph
        if year not in recipientMapping:
            recipientMapping[year] = {}
        if rid not in recipientMapping[year]:
            recipientMapping[year][rid] = {}
        if seat not in recipientMapping[year][rid]:
            recipientMapping[year][rid][seat] = \
                addRecipientFromTransaction(graph, transaction)
        rnodeid = recipientMapping[year][rid][seat]

        edgeID = graph.AddEdge(cnodeid, rnodeid)

        # Add a mapping from the year/tid to the edge ID
        if year not in edgeMapping:
            edgeMapping[year] = {}
        edgeMapping[year][tid] = edgeID

        # Add each edge attribute to the edge accordingly
        for attrib, index in transactionIndices.iteritems():
            val = transaction[index]
            addEdgeAttrib(graph, edgeID, val, attrib)

    return edgeMapping

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
    FOut = snap.TFOut(outfile)
    G.Save(FOut)
    FOut.Flush()

    # Save the edge, contributor, and recipient mappings to files in Data/Mappings
    mapPrefix = 'Data/Mappings/%d' % year
    pickler.save(contribMapping, mapPrefix + '.contribs')
    pickler.save(recipMapping, mapPrefix + '.recips')
    pickler.save(edgeMapping, mapPrefix + '.edges')

if __name__ == '__main__':
    for year in range(1980, 1996, 2):
        print 'Creating graph for %d' % year
        start = time.time()
        createAndSaveGraph(year)
        print 'Total time taken: %f' % (time.time() - start)
