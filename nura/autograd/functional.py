import numpy as np
import nura
from nura.tensors import Tensor
from typing import Dict, Generator, Tuple, Union, Optional, Callable, Any
from collections import deque


def backward(out: Tensor, grad: Optional[Tensor] = None) -> None:
    assert out.gradtensor and out.backfn
    if grad is None:
        assert out.nelem == 1
        grad = nura.oneslike(out)
    assert grad.gradtensor
    _backward(out, grad)


def _backward(out: Tensor, grad: Optional[Tensor] = None) -> None:
    queue = deque()
    queue.append((out.backfn, grad))

    while queue:
        node, grad = queue.popleft()
        nodes = node.children()
        tensor = node.tensor
        if tensor.leaf:
            assert isinstance(grad, Tensor)
            accumgrad = sumgrad(tensor, grad) if mismatch(tensor, grad) else grad
            oldgrad = (
                tensor.grad if nura.istensor(tensor.grad) else nura.zeroslike(tensor)
            )
            newgrad = oldgrad + accumgrad
            tensor.mutate(grad=newgrad.to(tensor.dtype))
        elif nodes:
            items = [[n, g] for n, g in zip(nodes, node.apply(grad, backward=True))]
            queue.extend(items)


def grad(
    inpt: Union[Tensor, Tuple[Tensor, ...]], out: Tensor, grad: Optional[Tensor] = None
) -> Tuple[Tensor, ...]:
    inpt = tupify(inpt)
    assert all(t.gradtensor for t in inpt)
    assert out.gradtensor
    assert out.backfn is not None
    if grad is None:
        assert out.nelem == 1
        grad = nura.oneslike(out)
    inptmap = _grad(inpt, out, grad)
    return tuple(inptmap.values())


def _grad(
    inpt: Tuple[Tensor, ...], out: Tensor, grad: Optional[Tensor] = None
) -> Dict[Tensor, Tensor]:
    grads = tuple(nura.zeroslike(t) for t in inpt)
    inptmap = mapify(inpt, grads)
    queue = deque()
    queue.append((out.backfn, grad))

    while queue:
        node, grad = queue.popleft()
        nodes = node.children()
        tensor = node.tensor
        if tensor in inptmap:
            assert isinstance(grad, Tensor)
            accumgrad = sumgrad(tensor, grad) if mismatch(tensor, grad) else grad
            oldgrad = inptmap[tensor]
            newgrad = oldgrad + accumgrad
            inptmap[tensor] = newgrad
        if nodes:
            items = [[n, g] for n, g in zip(nodes, node.apply(grad, backward=True))]
            queue.extend(items)
    return inptmap


def mapify(keys, values) -> Dict[Tensor, Any]:
    return {k: v for k, v in zip(keys, values)}


def mismatch(tensor: Tensor, grad: Tensor) -> bool:
    return tensor.dim != grad.dim and tensor.ndim <= grad.ndim


def sumgrad(tensor: Tensor, grad: Tensor) -> Tensor:
    dim = sumdims(tensor.dim, grad.dim, tensor.ndim, grad.ndim)
    keepdims = tensor.ndim == grad.ndim
    return grad.sum(dim=dim, keepdims=keepdims)


def sumdims(tdim, gdim, tndim, gndim) -> Tuple[int, ...]:
    paddim = np.pad(tdim, (gndim - tndim, 0), constant_values=0)
    mask = paddim != np.array(gdim)
    return tuple(np.where(mask)[0])


def tupify(inpt) -> Tuple[Tensor, ...]:
    if nura.istensor(inpt):
        return (inpt,)
    return inpt


def vjp(
    inpt: Union[Tuple[Tensor, ...], Tensor],
    vec: Tensor,
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tuple[Tensor, ...]]:

    inpt = tupify(inpt)
    assert all(t.gradtensor for t in inpt)
    assert vec.gradtensor
    inpt = tuple(t.mutated(usegrad=True, grad=None, leaf=True) for t in inpt)
    vec = vec.mutated(usegrad=False, grad=None)
    out, grads = _vjp(inpt, vec, f, *args, **kwargs)
    return out.mutated(usegrad=False, backfn=None, leaf=True), grads


def _vjp(
    inpt: Tuple[Tensor, ...],
    vec: Tensor,
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tuple[Tensor, ...]]:
    with nura.autograd(enabled=True, reverse=True, forward=False):
        out = f(*inpt, *args, **kwargs)
    inptmap = _grad(inpt, out, vec)
    return out, tuple(inptmap.values())


def jvp(
    inpt: Union[Tuple[Tensor, ...], Tensor],
    vec: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    inpt = tupify(inpt)
    vec = tupify(vec)
    assert all(t.gradtensor for t in inpt)
    assert all(v.gradtensor for v in vec)
    gen = (v for v in vec)
    inpt = tuple(t.mutated(usegrad=True, grad=next(gen)) for t in inpt)
    out, grad = _jvp(inpt, f, *args, **kwargs)
    return out.mutated(usegrad=False, leaf=True), grad


def _jvp(
    inpt: Tuple[Tensor, ...],
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:
    with nura.autograd(enabled=True, reverse=False, forward=True):
        out = f(*inpt, *args, **kwargs)
    assert out.grad is not None
    return out, out.grad


def jacrev(
    inpt: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    pos=0,
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    inpt = tupify(inpt)
    assert all(t.gradtensor for t in inpt)
    inpt = tuple(t.mutated(usegrad=True, grad=None, leaf=True) for t in inpt)
    with nura.autograd(enabled=True, reverse=True, forward=False):
        out = f(*inpt, *args, **kwargs)
    tensor = inpt[pos]
    jac = getjac(tensor, out)
    perts = getperts(out)

    for row, pert in zip(np.ndindex(out.dim), perts):
        rowinpt = tuple(map(lambda t: t.mutated(grad=None), inpt))
        _, grads = _vjp(rowinpt, pert, f, *args, **kwargs)
        jacrow = grads[pos]
        slc = row + (...,)
        jac[slc] = jacrow
    return out, jac


def jacfwd(
    inpt: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    pos=0,
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    inpt = tupify(inpt)
    assert all(t.gradtensor for t in inpt)
    with nura.autograd(enabled=False):
        out = f(*inpt, *args, **kwargs)
    tensor = inpt[pos]
    perts = getperts(tensor)
    jac = getjac(tensor, out)
    left = tuple(nura.zeroslike(inpt[i]) for i in range(pos))
    right = tuple(nura.zeroslike(inpt[i]) for i in range(pos + 1, len(inpt)))

    for col, pert in zip(np.ndindex(tensor.dim), perts):
        gen = (v for v in (left + (pert,) + right))
        colinpt = tuple(t.mutated(usegrad=True, grad=next(gen)) for t in inpt)
        _, jaccol = _jvp(colinpt, f, *args, **kwargs)
        slc = (...,) + col
        jac[slc] = jaccol
    return out, jac


def getperts(tensor: Tensor) -> Generator[Tensor, None, None]:
    nelem, dim, dtype = tensor.nelem, tensor.dim, tensor.dtype
    assert dtype is not None
    perts = nura.zeros((nelem,) + dim).to(dtype)
    arange = np.arange(nelem)
    indices = np.unravel_index(arange, dim)
    slc = (arange,) + indices
    perts[slc] = 1.0
    return (perts[i] for i in range(nelem))


def getjac(tensor: Tensor, out: Tensor) -> Tensor:
    dim = out.dim + tensor.dim
    assert out.dtype is not None
    jac = nura.zeros(dim).to(out.dtype)
    return jac
