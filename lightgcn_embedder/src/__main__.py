import torch
import multiprocessing
import argparse
from pathlib import Path
import pickle

from dataloader import DataLoader
from similarity import GraphSimilarity
from lightgcn import LightGCNTrainingConfig, LightGCNConfig, LightGCN
from loss import SimilarityLoss, BPRLoss
import utils
import training

CONFIGS_PATH = Path(__file__).parent.parent / "configs"
DATASET_CONFIG = CONFIGS_PATH / "datasets.json"
LOGS_PATH = Path(__file__).parent.parent / "results" / "logs"
EMBEDDINGS_PATH = Path(__file__).parent.parent / "results" / "embeddings"

if __name__ == "__main__":

    dataloader = DataLoader(DATASET_CONFIG)
    
    parser = argparse.ArgumentParser(description="Go lightGCN")
    parser.add_argument("--batch_size", type=int, default=2048, help="the batch size for training procedure")
    parser.add_argument("--dim", type=int, default=64, help="the embedding size of lightGCN")
    parser.add_argument("--layer", type=int, default=3, help="the layer num of lightGCN")
    parser.add_argument("--lr", type=float, default=0.001, help="the learning rate")
    parser.add_argument("--decay", type=float, default=1e-4, help="the weight decay for l2 normalizaton")
    parser.add_argument("--dropout", type=int, default=0, help="using the dropout or not")
    parser.add_argument("--keepprob", type=float, default=0.6, help="the dropout keep prob")
    parser.add_argument("--a_fold", type=int, default=100, help="the fold num used to split large adj matrix")
    parser.add_argument("--dataset", type=str, default="yelpnyc", help=f"available datasets: {dataloader.dataset_names}")
    parser.add_argument("--epochs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=5819, help="random seed")
    parser.add_argument("--loss", type=str, default="bpr", help="loss function, options: bpr, simi")
    parser.add_argument("--optimizer", type=str, default="adam", help="optimizer, options: adam, sgd")
    parser.add_argument("--name", type=str, default="", help="The name to add to the embs file and log file names.")
    args = parser.parse_args()

    logger = utils.configure_logger("Logger", LOGS_PATH, args.name, "info")
    dataset = dataloader.load_dataset(args.dataset)

    GPU = torch.cuda.is_available()
    device = torch.device("cuda" if GPU else "cpu")

    if GPU: 
        logger.info(f"CUDA GPA will be used for training.")
    else:
        logger.info(f"No GPU available. CPU will be used for training.")

    utils.set_seed(args.seed)
    logger.info(f"SEED: {args.seed}")

    # Set configurations
    train_config = LightGCNTrainingConfig(
        epochs = args.epochs,
        batch_size = args.batch_size,
        learning_rate = args.lr,
        dropout = args.dropout,
        weight_decay = args.decay
    )

    lightgcn_config = LightGCNConfig(
        latent_dim = args.dim,
        n_layers = args.layer,
        keep_prob = args.keepprob,
        A_split = args.a_fold,
        device = device,
        train_config = train_config
    )

    lightgcn = LightGCN(lightgcn_config, dataset, logger)

    if args.optimizer == "adam":
        optimizer = torch.optim.Adam(lightgcn.parameters(), lr=train_config.learning_rate, weight_decay=train_config.weight_decay)
    elif args.optimizer == "sgd":
        optimizer = torch.optim.SGD(lightgcn.parameters(), lr=train_config.learning_rate, weight_decay=train_config.weight_decay)
    else:
        logger.error(f"Optimizer {args.optimizer} is not supported.")
        raise ValueError(f"Optimizer {args.optimizer} is not supported.")
    
    if args.loss == "bpr":
        loss = BPRLoss(device, dataset, weight_decay=train_config.weight_decay)
        train_lightgcn = training.train_lightgcn_simi_loss
    elif args.loss == "simi":
        loss = SimilarityLoss(device, dataset, GraphSimilarity(dataset.graph_u2u), n_pos=10, n_neg=10, fast_sampling=False)
        train_lightgcn = training.train_lightgcn_simi_loss
    else:
        logger.error(f"Loss function {args.loss} is not supported.")
        raise ValueError(f"Loss function {args.loss} is not supported.")
            
    logger.info(f"Training LightGCN on {args.dataset} with {loss.__class__.__name__} loss function and {optimizer.__class__.__name__} optimizer.")

    for epoch in range(train_config.epochs):
        train_lightgcn(dataset, lightgcn, loss, optimizer, epoch, logger)

    user_embs, item_embs = lightgcn()
    embeddings_save_file = EMBEDDINGS_PATH / f'embs_{args.name}_{utils.current_timestamp()}.pkl'
    pickle.dump(user_embs, open(embeddings_save_file, 'wb'))
    logger.info(f"Saved user embeddings to {embeddings_save_file}")