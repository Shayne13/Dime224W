#!/usr/bin/python
# Module: sqlToGraphTests
# To call from the command line, run
# `python -m src.tests.sqlToGraphTests <years>`
# Where <years> contains each year whose graph you want to test.

import snap, sys
from ..util import graph_funcs
from ..tests.testUtil import runTest
from collections import defaultdict

################################################################################
# Test Functions #
################################################################################

# Function: testRecipients
# Tests that every recipient in the graph has a positive in-degree and a zero
# out-degree (i.e. every recipient is receiving donations but not giving any).
def testRecipients(graph):
    for recip in graph_funcs.getRecipients(graph):
        if recip.GetInDeg() > 0 and recip.GetOutDeg() == 0: continue
        return False

    return True

# Function: testDonors
# Tests that every donor in the graph has a positive out-degree and a zero
# in-degree (i.e. every donor is giving donations but not receiving any).
def testDonors(graph):
    for donor in graph_funcs.getDonors(graph):
        if donor.GetOutDeg() > 0 and donor.GetInDeg() == 0: continue
        return False

    return True

# Function: testAmounts
# Tests that every donor/recipient has net positive amounts donated/received
def testAmounts(graph):
    amounts = defaultdict(int)
    for edge in graph.Edges():
        amt = graph.GetIntAttrDatE(edge.GetId(), 'amount')
        amounts[edge.GetSrcNId()] += amt
        amounts[edge.GetDstNId()] += amt

    return min(amounts.values()) > 0

################################################################################
# Scaffolding functions #
################################################################################

# Run all the tests for a particular year
def runTestsForYear(year):
    print 'Testing year %d' % year
    graph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)
    args = (graph,)
    runTest('testRecipients', testRecipients, args)
    runTest('testDonors', testDonors, args)
    runTest('testAmounts', testAmounts, args)

# Called by the runTests script. Takes in a list of all the years whose graphs
# are to be tested and tests each of them.
def run(args):
    for year in args:
        runTestsForYear(int(year))

if __name__ == '__main__':
    run(sys.argv[1:])
