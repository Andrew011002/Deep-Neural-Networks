import nura
import nura.nn.functions as fn
import nura.utils as utils
from nura.tensors import Tensor
from nura.types import dimlike
from typing import Optional, Tuple, Union


def linear(x: Tensor, w: Tensor, b: Optional[Tensor] = None) -> Tensor:
    out = nura.matmul(x, w.T)
    if b is not None:
        out = out + b
    return out


def sigmoid(x: Tensor) -> Tensor:
    out = fn._Sigmoid.apply(x)
    return out


def tanh(x: Tensor) -> Tensor:
    out = fn._Tanh.apply(x)
    return out


def relu(x: Tensor) -> Tensor:
    out = fn._ReLU.apply(x)
    return out


def relu6(x: Tensor) -> Tensor:
    out = fn._ReLU6.apply(x)
    return out


def leakyrelu(x: Tensor, alpha=0.01):
    out = fn._LeakyReLU.apply(x, alpha)
    return out


def elu(x: Tensor, alpha=1.0):
    out = fn._ELU.apply(x, alpha)
    return out


def gelu(x: Tensor) -> Tensor:
    out = fn._GELU.apply(x)
    return out


def celu(x: Tensor, alpha=1.0) -> Tensor:
    out = fn._CELU.apply(x, alpha)
    return out


def softmax(x: Tensor, dim=-1) -> Tensor:
    out = fn._Softmax.apply(x, dim)
    return out


def attention(
    q: Tensor,
    k: Tensor,
    v: Tensor,
    mask: Optional[Tensor] = None,
    maskfill=-1e9,
) -> Tuple[Tensor, Tensor]:
    dk = k.dim[-1]
    simscore = nura.matmul(q, k.transpose(-1, -2)) / (dk**0.5)
    if mask is not None:
        simscore = utils.where(mask == True, simscore, maskfill)
    attn = softmax(simscore, -1)
    context = nura.matmul(attn, v)
    return context, attn


def embedding(x: Tensor, w: Tensor, padid: Optional[int] = None) -> Tensor:
    return fn._Embedding.apply(x, w, padid)


def binarycrossentropy(x: Tensor, y: Tensor) -> Tensor:
    return fn._BinaryCrossEntropy.apply(x, y)


def crossentropy(x: Tensor, y: Tensor, ignoreid: Optional[int] = None) -> Tensor:
    return fn._CrossEntropy.apply(x, y, ignoreid)


def dropout(x: Tensor, p: float = 0.5) -> Tensor:
    return fn._Dropout.apply(x, p)


def layernorm(
    x: Tensor,
    gamma: Tensor,
    beta: Tensor,
    dim: dimlike = -1,
    correction: int = 1,
    eps: float = 1e-5,
) -> Tensor:
    return fn._LayerNorm.apply(x, gamma, beta, dim, correction, eps)
