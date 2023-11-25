from similarity import *
import numpy as np
import pandas as pd
from functools import reduce


class AnomalyScore:
    def __init__(self, leaves, mapping, adj, metadata, avgratings):
        self.leaves = leaves
        self.mapping = mapping
        self.adj = adj
        self.metadata = metadata
        self.avgrating = avgratings


    def penalty_function(self, R_g, P_g):
        """
        Generates penalty function for the anomaly scores given a list of reviewers and products that they reviewed

        INPUTS:
        R_g (arr) - users in the group
        P_g (arr) - product sets in the group

        OUTPUTS:
        L_g (float) - review tightness for the group
        """
        R_gnorm = len(R_g)
        P_gnorm = len(P_g)
        L_g = 1 / (1 + np.e**(-1 * (R_gnorm + P_gnorm - 3)))
        return L_g


    def review_tightness(self, R_g, P_g):
        """
        Generates review tightness for the anomaly scores given a list of reviewers and products that they reviewed

        INPUTS:
        R_g (arr) - users in the group
        P_g (arr) - product sets in the group

        OUTPUTS:
        RT_g (float) - review tightness for the group
        """
        R_gnorm = len(R_g)
        P_gnorm = len(P_g)
        L_g = self.penalty_function(R_gnorm, P_gnorm)
        RT_g = (np.sum(P_g) * L_g) / (R_gnorm * P_gnorm)
        return RT_g


    def product_tightness(self, P_g):
        """
        Generates product tightness for the anomaly scores given a list of reviewers and products that they reviewed

        INPUTS:
        P_g (arr) - ndarr of product sets in the group

        OUTPUTS:
        PT_g (float) - product tightness for the group
        """
        PT_g = len(reduce(np.intersect1d, P_g)) / len(reduce(np.union1d, P_g))
        return PT_g
    
    
    def jaccard_similarity(self, s1, s2):
        """
        Compute Jaccard similarity between two NumPy arrays.

        INPUTS:
        s1 (ndarr) - first array.
        s2 (ndarr) - second array.
        
        OUTPUTS:
        js -  Jaccard similarity coefficient.
        """
        intersection = np.intersect1d(s1, s2)
        union = np.union1d(s1, s2)
        
        # Handle zero division error if union is empty
        if len(union) == 0:
            return 0.0
        
        js = len(intersection) / len(union)
        return js
    
    def sum_jaccard(self, arrays):
        """
        Compute Jaccard similarity between all pairs and sum the scores
        """
        if len(arrays) <= 1:
            return 0
    
        similarity_scores = [
            self.jaccard_similarity(arrays[i], arrays[j])
            for i in range(len(arrays))
            for j in range(i + 1, len(arrays))
        ]
        
        return sum(similarity_scores)


    def neighbor_tightness(self, R_g, P_g):
        """
        Generates product tightness for the anomaly scores given a list of reviewers and products that they reviewed

        INPUTS:
        R_g (arr) - users in the group
        P_g (arr) - product sets in the group

        OUTPUTS:
        
        PT_g (float) - product tightness for the group
        """
        R_gnorm = len(R_g)
        P_gnorm = len(P_g)
        js = self.sum_jaccard(P_g)
        L_g = self.penalty_function(R_gnorm, P_gnorm)
        NT_g = (2 * js * L_g) / R_gnorm
        return NT_g


    def AVRD(self):
        pass


    def BST(self):
        pass
    

    def generate_single_anomaly_score(self, R_g):
        """Generate single anomaly score"""
        
        P_g = self.adj[R_g]
        Π = 3 * self.review_tightness(R_g) * self.product_tightness() * self.neighbor_tightness()