import time

# Runs a particular test and reports the result, along with timing metrics.
# Takes in the test name, the function, and the params in a list in order.
# Returns whether test passed.
def runTest(testName, testFunc, args):
    print 'Running test ' + testName
    start = time.time()
    result = testFunc(*args)
    if result:
        print 'Passed test'
    else:
        print 'Failed test'
    print 'Total time elapsed: %f' % (time.time() - start)
    return result

# Run multiple tests which take the same arguments and reports which failed
def runMultipleTests(tests, args):
    results = {}
    for t in tests:
        results[t.__name__] = runTest(t.__name__, t, args)
    if all(results.values()):
        print 'Passed all tests!'
    else:
        for testName in results:
            if not results[testName]: print 'Failed %s' % testName
