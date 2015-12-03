#!/usr/bin/python
# Module: recip_feature_extractor
# Generates and saves the feature matrices for a particular cycle and weighting
# function, both for the main graph and for the basline
#
# To call from the command line, run `python src/recip_feature_extractor <years>`
# where years contains each year whose features you want to generate.

import sys, snap
import numpy as np
from collections import defaultdict
from util import pickler, graph_funcs
from util.Timer import Timer
from util.categorical import *

################################################################################
# Module functions #
################################################################################

# Given a bipartite donor-recipient graph and a dictionary from cnodeids to
# feature vectors, creates a dictionary from rnodeids to feature vectors.
def getRecipFeatures(graph, donorFeatures):
    timing = Timer('Getting recipient features')
    recipFeatures = {}

    # Load the donation amounts for cands, donors, and cand-donor combos
    receiptsFromDonor, totalReceipts, totalDonations = getDonationAmounts(graph)

    for recipNode in graph_funcs.getRecipients(graph, cfs=True):
        rnodeid = recipNode.GetId()

        # Add a donor feature indicating what percent of this donor's donations
        # went to this candidate.
        for donor in receiptsFromDonor[rnodeid]:
            pct = receiptsFromDonor[rnodeid][donor] / float(totalDonations[donor])
            donorFeatures[donor].append(pct)

        recipFeatures[rnodeid] = \
            processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid])
        #recipFeatures[rnodeid] = np.append(
        #    getPartialNodeRecipSpecificFeatures(graph, rnodeid),
        #    processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid])
        #)

        # Remove the temporarily added feature for what percent of this donor's
        # donations went to this candidate.
        for donor in receiptsFromDonor[rnodeid]:
            donorFeatures[donor].pop()

    timing.finish()
    return recipFeatures

# Creates a dictionary from rnodeids to feature vectors, where each feature vector
# has the node-specific features to be used in the baseline. To improve the quality
# of the baseline, this is restricted to full nodes for which all node specific
# features can be calculated.
def getBaselineFeatures(graph):
    features = {}
    for node in graph_funcs.getRecipients(graph, cfs=True, full=True):
        rnodeid = node.GetId()
        features[rnodeid] = getAllRecipSpecificFeatures(graph, rnodeid)

    return features

# Given a bipartite graph and a dictionary from rnodeids to feature vectors,
# constructs and returns the X feature matrix and Y vector. Can also apply a
# transformation function to Y (y_fun) or transformation functions to various
# columns of X (represented in x_funs as a dictionary from column indices to
# functions).
def featureDictToVecs(graph, featureDict, y_fun=None, x_funs=None):
    X = np.asarray([features for rnodeid, features in featureDict.iteritems()])
    Y = np.absolute([graph.GetFltAttrDatN(rnodeid, 'cfs') for rnodeid in featureDict])
    if y_fun:
        Y = y_fun(Y)
    if x_funs:
        for col, fun in x_funs.iteritems():
            X[:,col] = fun(X[:,col])
    return X, Y

# Given a graph, a dictionary from rnodeids to feature vectors, and optionally
# transformation functions to run on the Y vector and the columns of the X
# feature matrix (see featureDictToVecs), saves the X feature matrix and Y vector
# as a tuple to the designated file.
def saveFeatures(graph, featureDict, filename, y_fun=None, x_funs=None):
    X, Y = featureDictToVecs(graph, featureDict, y_fun=y_fun, x_funs=x_funs)
    pickler.save((X, Y), filename)

# Given a bipartite donor-recipient graph, creates one dictionary from int to
# dictionaries from ints to ints, and two dictionaries from ints to ints. The
# first shows, for a given candidate, the total donations from a given donor.
# The second and third show, for a given candidate or donor, how much they
# received or donated in total.
def getDonationAmounts(graph):
    timing = Timer('Getting candidate, donor, and cand-donor donation amounts')
    # A dictionary from rnodeids to dictionaries from cnodeids to floats indicating
    # the total donations from that donor to that candidate
    receiptsFromDonor = defaultdict(lambda: defaultdict(int))

    # A dictionary from rnodeids to ints indicating the total amount donated to
    # that candidate.
    totalReceipts = defaultdict(int)

    # A dictionary from cnodeids to ints indicating the total amount donated by
    # that donor.
    totalDonations = defaultdict(int)

    # For each donation, note it in the relevant dictionaries
    for edge in graph.Edges():
        donor = edge.GetSrcNId()
        recip = edge.GetDstNId()
        amount = graph.GetIntAttrDatE(edge.GetId(), 'amount')

        receiptsFromDonor[recip][donor] += amount
        totalReceipts[recip] += amount
        totalDonations[donor] += amount

    timing.finish()
    return receiptsFromDonor, totalReceipts, totalDonations

# Given the donor features and the weights this recipient should put on the donors
# (proportional to the percent of the recipient's donations coming from that donor),
# computes the portion of the recipient's feature vector dependent on the donor
# features.
#
# Currently only uses a weighted average. Will incorporate more summary stats
# later.
# TODO: Expand beyond just weighted average of network features (e.g. max, min,
# median, 25-75 percentiles, variance)
def processDonorFeaturesForRecip(donorFeatures, weightsForDonors):
    weights = [weightsForDonors[donor] for donor in weightsForDonors]
    unnormalizedFeatureVecs = [donorFeatures[donor] for donor in weightsForDonors]
    return np.average(unnormalizedFeatureVecs, weights=weights, axis=0)

# Creates a feature vector of the node features available only to full recipient
# nodes.
def getFullNodeRecipFeatures(graph, rnodeid):
    return np.zeros(0)

# Creates a feature vector of the node features available even to partial recipient
# nodes.
def getPartialNodeRecipFeatures(graph, rnodeid):
    return np.zeros(0)

# Creates a feature vector of features specific to this particular recipient node.
def getAllRecipSpecificFeatures(graph, rnodeid):
    return np.append(
        getFullNodeRecipFeatures(graph, rnodeid),
        getPartialNodeRecipFeatures(graph, rnodeid),
    )

################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    weightings = ('jaccard', 'jaccard2', 'affinity')
    for year in sys.argv[1:]:
        year = int(year)
        timing = Timer('Generating features for %d' % year)
        graph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)

        baselineFeatures = getBaselineFeatures(graph)
        saveFeatures(graph, baselineFeatures, 'Data/Recip-Features/%d.baseline' % year)
        timing.markEvent('Generated baseline features')

        for weighting in weightings:
            donorFeatures = pickler.load('Data/Features/%d%s.features' \
                    % (year, weighting))
            recipFeatures = getRecipFeatures(graph, donorFeatures)
            saveFeatures(graph, recipFeatures, 'Data/Recip-Features/%d.%s' \
                    % (year, weighting))
            timing.markEvent('Calculated main recipient features for %s' \
                    % weighting)

        timing.finish()

