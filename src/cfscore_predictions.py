import snap, time
import numpy as np
from collections import defaultdict
from sklearn.cross_validation import KFold
from sklearn import linear_model
from util import pickler

def trainAndTestModels(year, weighting, k = 10, clf = linear_model.LinearRegresion()):
    print 'Running on year %d and weighting function %s' % (year, weighting)
    start = time.time()

    # Load the raph and donor features
    print 'Loading old graphs and features'
    bigraph = snap.TNEANet.Load(snap.TFIn('Data/Bipartite-Graphs/%d.graph' % year))
    donorFeatures = pickler.load('Data/Features/%d%s.features' % (year, weighting))
    print 'Time elapsed: %f' % (time.time() - start)

    # Calculate the recipient features
    print 'Calculating recipient feaures'
    recipFeatures = getRecipFeatures(bigraph, donorFeatures)
    print 'Time elapsed: %f' % (time.time() - start)

    # Convert the features and node cfscore attributes into X and Y matrices for
    # sklearn to use
    print 'Running regression'
    X = np.asarray([features for rnodeid, features in recipFeatures.iteritems()])
    Y = np.absolute([bigraph.GetIntAttrDatN(rnodeid, 'cfs') for rnodeid in recipFeatures])

    rsquareds = []

    # Train and test the regression model on each k-fold set
    kf = KFold(len(Y), k)
    for train, test in kf:
        X_train, X_test = X[train], X[test]
        Y_train, Y_test = Y[train], Y[test]
        clf.fit(X_train, Y_train)
        rsquareds.append(clf.score(X_test, Y_test))
    print 'Time elapsed: %f' % (time.time() - start)

    avgRSq = sum(rsquareds) / len(rsquareds)
    with open('Data/Results/%d%s.rsquareds', 'w') as f:
        f.write('K-fold validation results:\n')
        f.write('Average: %f\n\n' % r)
        for i, r in enumerate(rsquareds):
            f.write('%d: %f\n' % (i, r))

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
    donationsToCand = defaultdict(lambda: defaultdict(float))

    # A dictionary from cnodeids to ints indicating the total amount donated by
    # that donor.
    totalDonations = defaultdict(int)

    # For each donation, note it in the relevant dictionaries
    for edge in graph.Edges():
        donor = edge.GetSrcId()
        recip = edge.GetDstId()
        amount = graph.GetIntAttrDatN(edge.GetId(), 'amount')

        receiptsFromDonor[recip][donor] += amount
        totalReceipts[recip] += amount
        donationsToCand[donor][recip] += amount
        totalDonations[donor] += amount

    # Normalize the receiptsFromDonor and donationsToCand dictionaries to be
    # percentages of the relevant total rather than raw dollar amounts
    for recip in totalReceipts:
        for donor in totalDonations:
            receiptsFromDonor[recip][donor] /= float(totalReceipts[recip])
            donationsToCand[donor][recip] /= float(totalDonations[donor])

    return receiptsFromDonor, donationsToCand, totalReceipts, totalDonations

# Given a bipartite donor-recipient graph and a dictionary from cnodeids to
# feature vectors, creates a dictionary from rnodeids to feature vectors.
def getRecipFeatures(graph, donorFeatures):
    recipFeatures = {}

    receiptsFromDonor, donationsToCand, totalReceipts, totalDonations = \
            getAmountPercentages(graph)

    for node in graph.Nodes():
        rnodeid = node.GetId()
        if graph.GetIntAttrDatN(rnodeid, 'IsRecip') != 1:
            continue

        for donor in receiptsFromDonor[rnodeid]:
            donorFeatures[donor].append(donationsToCand[rnodeid][donor])

        recipFeatures[rnodeid] = np.append(
            getRecipSpecificFeatures(graph, rnodeid),
            processDonorFeaturesForRecip(donorFeatures, receiptsFromDonor[rnodeid])
        )

        for donor in receiptsFromDonor[rnodeid]:
            donorFeatures[donor].pop()

    return recipFeatures


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
    weights = [weight for donor, weight in weightsForDonors.iteritems()]
    unnormalizedFeatureVecs = \
        np.asarray([donorFeatures[donor] for donor in weightsForDonors])
    return np.average(unnormalizedFeatureVecs, weights=weights, axis=0)


# Creates a feature vector of features specific to this particular recipient node.
# Currently unimplmented.
# TODO: Add actual features
def getRecipSpecificFeatures(graph, rnodeid):
    return np.zeros(0)
