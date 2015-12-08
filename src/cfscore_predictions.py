#!/usr/bin/python
# Module: cfscore_predictions
# Runs the regression for a particular saved X matrix and Y vector
#
# To call from the command line, run `python src/cfscore_predictions <years>
# where years contains each year whose regression you want run.

import sys
import numpy as np
from sklearn.cross_validation import KFold
from sklearn import linear_model
from util import pickler
from util.Timer import Timer

################################################################################
# Module functions #
################################################################################

def trainAndTestModels(year, extension, k = 10,
        clf = linear_model.LinearRegression(),
        transF = None):
    timing = Timer('Running regression for %d.%s' % (year, extension))
    X, Y = pickler.load('Data/Recip-Features/%d.%s' % (year, extension))
    if transF: Y = transF(Y)
    timing.markEvent('Loaded X and Y')
    rsquareds = []

    # Train and test the regression model on each k-fold set
    kf = KFold(len(Y), k)
    for train, test in kf:
        X_train, X_test = X[train], X[test]
        Y_train, Y_test = Y[train], Y[test]
        clf.fit(X_train, Y_train)
        rsquareds.append(clf.score(X_test, Y_test))
    timing.markEvent('Ran regression')

    timing.finish()
    return rsquareds

################################################################################
# Module command-line behavior #
################################################################################

if __name__ == '__main__':
    extensions = ('jaccard', 'jaccard2', 'affinity', 'cosine', 'adamic', 'weighted_adamic', 'baseline')
    for year in sys.argv[1:]:
        year = int(year)
        timing = Timer('Running regressions for %d' % year)
        for extension in extensions:
            rsquareds = trainAndTestModels(year, extension)
            avgRSq = sum(rsquareds) / len(rsquareds)
            print '%d %s: %f' % (year, extension, avgRSq)
            with open('Data/Results/%d.%s' % (year, extension), 'w') as f:
                f.write('K-fold validation results:\n')
                f.write('Average: %f\n\n' % avgRSq)
                for i, r in enumerate(rsquareds):
                    f.write('%d: %f\n' % (i, r))
