import time

# Runs a particular test and reports the result, along with timing metrics.
# Takes in the test name, the function, and the params in a list in order.
def runTest(testName, testFunc, args):
    print 'Running test ' + testName
    start = time.time()
    if testFunc(*args):
        print 'Passed test'
    else:
        print 'Failed test'
    print 'Total time elapsed: %f' % (time.time() - start)
