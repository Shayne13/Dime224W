import snap, scipy, sklearn
from collections import defaultdict
import numpy as np

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

    # Normalize 
    for recip in totalReceipts:
        for donor in totalDonations:
            receiptsFromDonor[recip][donor] /= totalReceipts[recip]
            donationsToCand[donor][recip] /= totalDonations[donor]

    return receiptsFromDonor, donationsToCand
