from openchem.models.Graph2Label import Graph2Label
from openchem.modules.encoders.gcn_encoder import GraphCNNEncoder
from openchem.modules.mlp.openchem_mlp import OpenChemMLP
from openchem.data.graph_data_layer import GraphDataset

from openchem.utils.graph import Attribute
from openchem.utils.utils import identity

import torch.nn as nn
from torch.optim import RMSprop, SGD, Adam
from torch.optim.lr_scheduler import ExponentialLR, StepLR
import torch.nn.functional as F
from sklearn.metrics import r2_score, mean_squared_error

import pandas as pd
import numpy as np

import copy
import pickle


def get_atomic_attributes(atom):
    attr_dict = {}
  
    atomic_num = atom.GetAtomicNum()
    atomic_mapping = {5: 0, 7: 1, 6: 2, 8: 3, 9: 4, 15: 5, 16: 6, 17: 7, 35: 8,
                      53: 9}
    if atomic_num in atomic_mapping.keys():
        attr_dict['atom_element'] = atomic_mapping[atomic_num]
    else:
        attr_dict['atom_element'] = 10
    attr_dict['valence'] = atom.GetTotalValence()
    attr_dict['charge'] = atom.GetFormalCharge()
    attr_dict['hybridization'] = atom.GetHybridization().real
    attr_dict['aromatic'] = int(atom.GetIsAromatic())
    attr_dict['mol_weight'] = float(atom.GetMass())
    return attr_dict


node_attributes = {}
node_attributes['valence'] = Attribute('node', 'valence', one_hot=True, values=[1, 2, 3, 4, 5, 6])
node_attributes['charge'] = Attribute('node', 'charge', one_hot=True, values=[-1, 0, 1, 2, 3, 4])
node_attributes['hybridization'] = Attribute('node', 'hybridization',
                                             one_hot=True, values=[0, 1, 2, 3, 4, 5, 6, 7])
node_attributes['aromatic'] = Attribute('node', 'aromatic', one_hot=True,
                                        values=[0, 1])
node_attributes['atom_element'] = Attribute('node', 'atom_element',
                                            one_hot=True,
                                            values=list(range(11)))
node_attributes['mol_weight'] = Attribute('node', 'mol_weight',
                                            one_hot=False)


from openchem.data.utils import read_smiles_property_file
data = read_smiles_property_file('./benchmark_datasets/logs_dataset/water_solubility_data.csv',
                                         cols_to_read=[1,2], keep_header=False)

smiles = data[0]
labels = np.array(data[1]).reshape(-1, 1)

from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(smiles, labels, test_size=0.2,
                                                            random_state=42)

from openchem.data.utils import save_smiles_property_file
save_smiles_property_file('./benchmark_datasets/logs_dataset/train.smi', X_train, y_train)
save_smiles_property_file('./benchmark_datasets/logs_dataset/test.smi', X_test, y_test)


train_dataset = GraphDataset(get_atomic_attributes, node_attributes,
                             './benchmark_datasets/logs_dataset/train.smi',
                             delimiter=',', cols_to_read=[0, 1])
test_dataset = GraphDataset(get_atomic_attributes, node_attributes,
                             './benchmark_datasets/logs_dataset/test.smi',
                             delimiter=',', cols_to_read=[0, 1])

predict_dataset = GraphDataset(get_atomic_attributes, node_attributes,
                               './benchmark_datasets/logs_dataset/test.smi',
                               delimiter=',', cols_to_read=[0],
                               return_smiles=True)

model = Graph2Label

model_params = {
    'task': 'regression',
    'random_seed': 42,
    'use_clip_grad': False,
    'batch_size': 256,
    'num_epochs': 101,
    'logdir': 'logs/logs_gcnn_logs',
    'print_every': 1,
    'save_every': 5,
    'train_data_layer': train_dataset,
    'val_data_layer': test_dataset,
    'predict_data_layer': predict_dataset,
    'eval_metrics': r2_score,
    'criterion': nn.MSELoss(),
    'optimizer': Adam,
    'optimizer_params': {
        'lr': 0.0005,
    },
    'lr_scheduler': StepLR,
    'lr_scheduler_params': {
        'step_size': 15,
        'gamma': 0.8
    },
    'encoder': GraphCNNEncoder,
    'encoder_params': {
        'input_size': train_dataset[0]["node_feature_matrix"].shape[1],
        'encoder_dim': 128,
        'n_layers':10,
        'hidden_size': [256, 256, 256, 256, 256, 256, 256, 256, 256, 256],
    },
    'mlp': OpenChemMLP,
    'mlp_params': {
        'input_size': 128,
        'n_layers': 2,
        'hidden_size': [128, 1],
        'activation': [F.leaky_relu, identity]
    }
}

