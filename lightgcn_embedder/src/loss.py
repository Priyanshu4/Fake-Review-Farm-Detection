from lightgcn import LightGCN, LightGCNConfig
import numpy as np
from dataloader import BasicDataset
import torch
import sampling
from similarity import GraphSimilarity

class ModelLoss:


    def __init__(self, device: torch.device, dataset: BasicDataset):
        self.device = device
        self.dataset = dataset
        pass

    def get_loss(self):
        pass

class SimilarityLoss(ModelLoss):
    """The similarity loss from DeepFD will be applied to LightGCN for embeddings.
       Similarities are only computed between each node and its samples to avoid computing all pairwise similarities.
    """

    def __init__(self, device: torch.device, dataset: BasicDataset, graph_simi: GraphSimilarity, n_pos: int, n_neg: int, fast_sampling: bool = False):
        super().__init__(device, dataset)
        self.graph_simi = graph_simi
        self.n_pos = n_pos
        self.n_neg = n_neg
        self.fast_sampling = fast_sampling

    def get_loss(self, user_nodes, user_embs, extended_user_nodes_batch, samples):
        """ 
        Arguments:
            user_nodes: list of user node indices
            user_embs: tensor of user embeddings
            extended_user_nodes_batch: generated by extend_user_node_batch
            samples: 2D numpy array of pos/neg samples of each node
                samples should be generated once per epoch by sample_train_set_pos_neg_users
        """
        node2index = {n: i for i, n in enumerate(extended_user_nodes_batch)}
        simi_feat = []
        simi_embs = []
        for node_i in user_nodes:
            for sample_index in range(samples.shape[1]):
                node_j = samples[node_i, sample_index]
                simi_feat.append(torch.FloatTensor([self.graph_simi[node_i, node_j]]))
                dis_ij = (user_embs[node2index[node_i]] - user_embs[node2index[node_j]]) ** 2
                dis_ij = torch.exp(-dis_ij.sum())
                simi_embs.append(dis_ij.view(1))
        simi_feat = torch.cat(simi_feat, 0).to(self.device)
        simi_embs = torch.cat(simi_embs, 0)
        L = simi_feat * ((simi_embs - simi_feat) ** 2)
        return L.mean()
    
    def sample_train_set_pos_neg_users(self):
        return sampling.sample_train_set_pos_neg_users(self.dataset, self.n_pos, self.n_neg, self.fast_sampling)

    @staticmethod
    def extend_user_node_batch(user_nodes, samples):
        """ Extends the batch of user nodes with their samples.
        """
        extended_nodes_batch = set(user_nodes)
        for node_i in user_nodes:
            extended_nodes_batch |= set(samples[node_i])
        
        return np.array(list(extended_nodes_batch))

class BPRLoss(ModelLoss):

    def __init__(self, device: torch.device, dataset: BasicDataset, weight_decay: float):
        super().__init__(device, dataset)
        self.weight_decay = weight_decay

    def get_loss(self, users_emb, pos_emb, neg_emb, users_emb_ego, pos_emb_ego, neg_emb_ego):
        loss, reg_loss = self.bpr_loss(users_emb, pos_emb, neg_emb, users_emb_ego, pos_emb_ego, neg_emb_ego)
        reg_loss = reg_loss * self.weight_decay
        loss = loss + reg_loss
        return loss

    def bpr_loss(self, users_emb, pos_emb, neg_emb, users_emb_ego, pos_emb_ego, neg_emb_ego):
        reg_loss = (1/2)*(users_emb_ego.norm(2).pow(2) + 
                         pos_emb_ego.norm(2).pow(2)  +
                         neg_emb_ego.norm(2).pow(2))/float(len(users_emb))
        pos_scores = torch.mul(users_emb, pos_emb)
        pos_scores = torch.sum(pos_scores, dim=1)
        neg_scores = torch.mul(users_emb, neg_emb)
        neg_scores = torch.sum(neg_scores, dim=1)

        loss = torch.mean(torch.nn.functional.softplus(neg_scores - pos_scores))
        
        return loss, reg_loss
    
