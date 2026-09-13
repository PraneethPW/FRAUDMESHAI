"""Small CPU graph neural network with learned relation-specific mean message passing.

h_r = tanh(mean_{j in N_r(t)} decay(t-t_j) x_j W_r + b_r)
h_tx = tanh(x_tx W_self + b_self)
p = sigmoid([h_tx, h_account, h_device, h_ip, h_merchant] w + b)

NumPy backpropagation and Adam keep training/inference deployable without CUDA.
This is a time-decayed GraphSAGE-style model, not a TGN memory or TGAT implementation.
"""

import numpy as np


def sigmoid(x):
    return 1 / (1 + np.exp(-np.clip(x, -30, 30)))


def forward(weights, x, messages):
    own = np.tanh(x @ weights["self_w"] + weights["self_b"])
    neighbors = np.tanh(np.einsum("nrf,rfh->nrh", messages, weights["message_w"]) + weights["message_b"])
    hidden = np.concatenate([own, neighbors.reshape(len(x), -1)], axis=1)
    return sigmoid(hidden @ weights["out_w"] + weights["out_b"]), (own, neighbors, hidden)


def fit(x, m, y, seed=42, epochs=150):
    rng = np.random.default_rng(seed)
    width = 12
    w = {
        "self_w": rng.normal(0, 0.15, (10, width)),
        "self_b": np.zeros(width),
        "message_w": rng.normal(0, 0.15, (4, 10, width)),
        "message_b": np.zeros((4, width)),
        "out_w": rng.normal(0, 0.15, width * 5),
        "out_b": np.zeros(1),
    }
    first = {k: np.zeros_like(v) for k, v in w.items()}
    second = {k: np.zeros_like(v) for k, v in w.items()}
    class_weight = np.where(y == 1, len(y) / (2 * max(y.sum(), 1)), len(y) / (2 * max((1 - y).sum(), 1)))
    for step in range(1, epochs + 1):
        p, (own, neighbors, hidden) = forward(w, x, m)
        dz = (p - y) * class_weight / len(y)
        dh = dz[:, None] * w["out_w"][None, :]
        ds = dh[:, :width] * (1 - own**2)
        dn = dh[:, width:].reshape(neighbors.shape) * (1 - neighbors**2)
        grads = {
            "out_w": hidden.T @ dz,
            "out_b": np.array([dz.sum()]),
            "self_w": x.T @ ds,
            "self_b": ds.sum(axis=0),
            "message_w": np.einsum("nrf,nrh->rfh", m, dn),
            "message_b": dn.sum(axis=0),
        }
        for key, g in grads.items():
            g = np.clip(g + 1e-4 * w[key], -5, 5)
            first[key] = 0.9 * first[key] + 0.1 * g
            second[key] = 0.999 * second[key] + 0.001 * g * g
            w[key] -= 0.015 * (first[key] / (1 - 0.9**step)) / (np.sqrt(second[key] / (1 - 0.999**step)) + 1e-8)
    return {k: v.tolist() for k, v in w.items()}
