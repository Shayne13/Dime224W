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

        recipFeatures[rnodeid] = processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid])
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
    Y = np.asarray([graph.GetFltAttrDatN(rnodeid, 'cfs') for rnodeid in featureDict])
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
# Currently calculates min, max, mean, median, 25-quantile, 75-quantile and variance.
def processDonorFeaturesForRecip(donorFeatures, weightsForDonors):
    # NB: Everything added to features (not 'squares') is weighted
    features = []
    
    weights = [weightsForDonors[donor] for donor in weightsForDonors]
    unnormalizedFeatureVecs = np.array([donorFeatures[donor] for donor in weightsForDonors])
    squares = []
    
    # Iterate over the columns (distribution for a feature) calculating quantiles and squares.
    for col in range(len(unnormalizedFeatureVecs[0])):
        quantiles = weighted_quantile(unnormalizedFeatureVecs[:,col], [0.0, 0.25, 0.5, 0.75, 1.0], sample_weight=weights)
        squares.append(np.square(unnormalizedFeatureVecs[:,col]))
        print quantiles.tolist()
        features += quantiles.tolist()
    
    averages = np.average(unnormalizedFeatureVecs, weights=weights, axis=0).tolist()
    variances = (np.average(squares, weights=weights, axis=1) - np.square(averages)).tolist()

    features = features + averages + variances
    return features


# This calculates weighted quantiles.
# Modified from https://stackoverflow.com/questions/21844024/weighted-percentile-using-numpy.
def weighted_quantile(values, quantiles, sample_weight=None, values_sorted=False, old_style=False):
    """ Very close to numpy.percentile, but supports weights.
    NOTE: quantiles should be in [0, 1]!
    :param values: numpy.array with data
    :param quantiles: array-like with many quantiles needed
    :param sample_weight: array-like of the same length as `array`
    :param values_sorted: bool, if True, then will avoid sorting of initial array
    :param old_style: if True, will correct output to be consistent with numpy.percentile.
    :return: numpy.array with computed quantiles.
    """
    values = np.array(values)
    quantiles = np.array(quantiles)
    if sample_weight is None:
        sample_weight = np.ones(len(values))
    sample_weight = np.array(sample_weight)

    assert np.all(quantiles >= 0) and np.all(quantiles <= 1), 'quantiles should be in [0, 1]'

    if not values_sorted:
        sorter = np.argsort(values)
        values = values[sorter]
        sample_weight = sample_weight[sorter]

    weighted_quantiles = np.cumsum(sample_weight) - 0.5 * sample_weight

    if old_style:
        # To be convenient with numpy.percentile
        weighted_quantiles -= weighted_quantiles[0]
        weighted_quantiles /= weighted_quantiles[-1]
    else:
        weighted_quantiles /= np.sum(sample_weight)

    return np.interp(quantiles, weighted_quantiles, values)



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

#####################################################################r###########
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
