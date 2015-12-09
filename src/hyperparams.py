import sys, cfscore_predictions
from util import pickler
from util.Timer import Timer
from sklearn.decomposition import PCA, FastICA, FactorAnalysis
import numpy as np
from sklearn import linear_model, ensemble

decompFunctions = {
        'None': None,
        'PCA': PCA(n_components='mle'),
        #'Factor Analysis': FactorAnalysis(n_components='mle'),
        #'ICA': FastICA(n_components='mle'),
}

clfs = {
        'OLS': linear_model.LinearRegression(),
        'Random Forest': ensemble.RandomForestRegressor(),
}

extensions = ('jaccard', 'jaccard2', 'cosine', 'adamic', 'weighted_adamic')

results = {}
resultsList = []

years = [int(arg) for arg in sys.argv[1:]]
timing = Timer('Runnign everything')
for year in years:
    timing.markEvent('Running for year %d' % year)
    results[year] = {}
    for extension in extensions:
        timing.markEvent('Running for extension %s' % extension)
        results[year][extension] = {}
        for clfname, clf in clfs.iteritems():
            timing.markEvent('Running for classifier %s' % clfname)
            results[year][extension][clfname] = {}
            for decompname, decompFunction in decompFunctions.iteritems():
                timing.markEvent('Running for decomp function %s' % decompname)
                rsquareds = cfscore_predictions.trainAndTestModels(
                        year, extension, clf=clf, decomp_func=decompFunction)
                resultsList.append((year, extension, clfname, decompname, tuple(rsquareds)))
                results[year][extension][clfname][decompname] = tuple(rsquareds)
                timing.markEvent('Done')

timing.finish()
print results
pickler.save(results, 'results')
pickler.save(resultsList, 'resultsList')
