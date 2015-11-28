import snap
import numpy as np
from collections import defaultdict
from sklearn.cross_validation import KFold
from sklearn import linear_model
from util import pickler, graph_funcs
from util.Timer import Timer

def trainAndTestModels(year, weighting, k = 10, clf = linear_model.LinearRegression()):
    timing = Timer('year %d and weighting function %s' % (year, weighting))

    # Load the raph and donor features
    bigraph = graph_funcs.loadGraph('Data/Bipartite-Graphs/%d.graph' % year)
    donorFeatures = pickler.load('Data/Features/%d%s.features' % (year, weighting))
    timing.markEvent('Loaded old graphs and features')

    # Calculate the recipient features
    recipFeatures = getRecipFeatures(bigraph, donorFeatures)
    timing.markEvent('Calculated recipient features')

    # Convert the features and node cfscore attributes into X and Y matrices for
    # sklearn to use
    print len(recipFeatures)
    X = np.asarray([features for rnodeid, features in recipFeatures.iteritems()])
    print X
    Y = np.absolute([bigraph.GetIntAttrDatN(rnodeid, 'cfs') for rnodeid in recipFeatures])
    print Y

    rsquareds = []

    # Train and test the regression model on each k-fold set
    kf = KFold(len(Y), k)
    for train, test in kf:
        X_train, X_test = X[train], X[test]
        Y_train, Y_test = Y[train], Y[test]
        clf.fit(X_train, Y_train)
        rsquareds.append(clf.score(X_test, Y_test))
    timing.markEvent('Ran regression')

    avgRSq = sum(rsquareds) / len(rsquareds)
    with open('Data/Results/%d%s.rsquareds' % (year, weighting), 'w') as f:
        f.write('K-fold validation results:\n')
        f.write('Average: %f\n\n' % avgRSq)
        for i, r in enumerate(rsquareds):
            f.write('%d: %f\n' % (i, r))
    timing.finish()

# Given a bipartite donor-recipient graph, creates two dictionaries from int to
# dictionaries from ints to floats, and two dictionaries from ints to ints. The
# first shows, for a given candidate, what percentage of their donations came
# from a given donor. The second shows, for a given donor, what percentge of
# their donations went to a given candidate. The third and fourth show, for a
# given candidate or donor, how much they received or donated in total.
def getAmountPercentages(graph):
    # A dictionary from rnodeids to dictionaries from cnodeids to floats indicating
    # the percent of the cand's donations that came from that donor.
    receiptsFromDonor = defaultdict(lambda: defaultdict(float))

    # A dictionary from rnodeids to ints indicating the total amount donated to
    # that candidate.
    totalReceipts = defaultdict(int)

    # A dictionary from cnodeids to dictionaries from rnodeids to floats indicating
    # the percent of the donor's donations that went to that cand
    #donationsToCand = defaultdict(lambda: defaultdict(float))

    # A dictionary from cnodeids to ints indicating the total amount donated by
    # that donor.
    #totalDonations = defaultdict(int)

    # For each donation, note it in the relevant dictionaries
    for edge in graph.Edges():
        donor = edge.GetSrcNId()
        recip = edge.GetDstNId()
        amount = graph.GetIntAttrDatE(edge.GetId(), 'amount')

        receiptsFromDonor[recip][donor] += amount
        totalReceipts[recip] += amount
        #donationsToCand[donor][recip] += amount
        #totalDonations[donor] += amount
    print 'Created unnormalized donation dicts'

    # Normalize the receiptsFromDonor and donationsToCand dictionaries to be
    # percentages of the relevant total rather than raw dollar amounts
    i = 0
    print len(totalReceipts)
    for recip in totalReceipts:
        if totalReceipts[recip] == 0:
            i += 1
            print 'Failed on %d, node %d' % (i, recip)
            continue
        for donor in receiptsFromDonor[recip]:
            #if totalDonations[donor] == 0:
            #    print 'Zero on donor %d' % donor
            receiptsFromDonor[recip][donor] /= float(totalReceipts[recip])
            #donationsToCand[donor][recip] /= float(totalDonations[donor])
    print 'Created normalized donation dicts'

    return receiptsFromDonor, totalReceipts
    #return receiptsFromDonor, donationsToCand, totalReceipts, totalDonations

# Given a bipartite donor-recipient graph and a dictionary from cnodeids to
# feature vectors, creates a dictionary from rnodeids to feature vectors.
def getRecipFeatures(graph, donorFeatures):
    recipFeatures = {}

    #print 'Getting amount percentages.'
    receiptsFromDonor, totalReceipts = getAmountPercentages(graph)
    #receiptsFromDonor, donationsToCand, totalReceipts, totalDonations = \
    #        getAmountPercentages(graph)
    #print 'Got amount percentages.'

    good = 0
    bad = 0
    for rnodeid in graph_funcs.getRecipients(graph):
        #for donor in receiptsFromDonor[rnodeid]:
        #    donorFeatures[donor].append(donationsToCand[rnodeid][donor])

        if validWeights(donorFeatures, receiptsFromDonor[rnodeid]):
            recipFeatures[rnodeid] = processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid])
            good += 1
        else:
            bad += 1
            #recipFeatures[rnodeid] = np.append(
            #    processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid]),
            #    getRecipSpecificFeatures(graph, rnodeid)
            #)

        #for donor in receiptsFromDonor[rnodeid]:
        #    donorFeatures[donor].pop()

    print 'Good: %d; Bad: %d' % (good, bad)
    return recipFeatures

def validWeights(donorFeatures, weightsForDonors):
    eligibleDonors = set(weightsForDonors.keys()) & set(donorFeatures.keys())
    return sum(weightsForDonors[donor] for donor in eligibleDonors) > 0

# Given the donor features and the weights this recipient should put on the donors
# (proportional to the percent of the recipient's donations coming from that donor),
# computes the portion of the recipient's feature vector dependent on the donor
# features.
#
# Currently only uses a weighted average. Will incorporate more summary stats
# later.
# TODO: Expand beyond just weighted average of network features (e.g. max, min,
# median, 25-75 split, variance)
def processDonorFeaturesForRecip(donorFeatures, weightsForDonors):
    eligibleDonors = set(weightsForDonors.keys()) & set(donorFeatures.keys())
    weights = [weightsForDonors[donor] for donor in eligibleDonors]
    unnormalizedFeatureVecs = \
        np.asarray([donorFeatures[donor] for donor in eligibleDonors])
    #print np.average(unnormalizedFeatureVecs, weights=weights, axis=0)
    return np.average(unnormalizedFeatureVecs, weights=weights, axis=0)


# Creates a feature vector of features specific to this particular recipient node.
# Currently unimplmented.
# TODO: Add actual features
def getRecipSpecificFeatures(graph, rnodeid):
    return np.zeros(0)

if __name__ == '__main__':
    weightings = ['jaccard', 'jaccard2', 'affinity']
    for w in weightings:
        trainAndTestModels(1980, w, 4)
