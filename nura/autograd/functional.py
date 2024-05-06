import numpy as np
import nura
from nura.tensors import Tensor
from nura.autograd.graph import Node, construct_graph, topological
from typing import Dict, Generator, Tuple, Optional, Callable, Union, List, Set
from collections import deque
from timeit import default_timer as timer


def backward(
    outputs: Union[Tuple[Tensor, ...], Tensor],
    grads: Optional[Union[Tuple[Tensor, ...], Tensor]] = None,
    inputs: Optional[Union[Tuple[Tensor, ...], Tensor]] = None,
) -> None:
    outputs, grads, inputs = _tupify(outputs), _tupify(grads), _tupify(inputs)
    _backward(outputs, grads, inputs)


def _backward(
    outputs: Tuple[Tensor, ...],
    grads: Tuple[Tensor, ...],
    inputs: Tuple[Tensor, ...],
) -> None:
    start = timer()
    output_nodes = tuple(o.gradfn for o in outputs if o.gradfn is not None)
    inputs_nodes = tuple(o.gradfn for o in inputs if o.gradfn is not None)
    graph = construct_graph(output_nodes)
    node_order = topological(graph)
    accumulates = _get_accumulates(node_order, inputs_nodes)
    output_grads = _get_output_grads(outputs, grads, output_nodes)
    grad_map = {node: grads for node, grads in zip(output_nodes, output_grads)}
    queue = deque(node_order)

    while queue:
        node = queue.popleft()
        node_grads = grad_map[node]
        if node in accumulates:
            node.accumulate(*node_grads)
        else:
            edge_grads = node.apply(*node_grads)
            for (edge_node, index), edge_grad in zip(node.edges, edge_grads):
                if edge_node is None:
                    continue
                if edge_node not in grad_map:
                    grad_map[edge_node] = [
                        nura.zeroslike(output) for output in edge_node.outputs
                    ]
                grad_map[edge_node][index] += edge_grad
        grad_map.pop(node)
    end = timer()
    print(f"Elapsed time: {end - start:.10f}s")

def _sum_grad(output: Tensor, grad: Tensor):
    pad = np.pad(output.dim, grad.ndim - output.ndim, constant_values=0)
    dim = tuple(np.where(pad != np.array(grad.dim))[0])
    grad.sum(dim=dim).reshape(output.dim)
    pass


def _get_accumulates(
    nodes: Tuple[Node, ...], input_nodes: Tuple[Node, ...]
) -> Set[Node]:
    accumulates = set()
    for node in nodes:
        if node._retained_outputs is not None and any(node._retained_outputs):
            accumulates.add(node)
    accumulates.update(input_nodes)
    return accumulates


def _get_output_grads(
    outputs: Tuple[Tensor, ...],
    grads: Tuple[Tensor, ...],
    output_nodes: Tuple[Node, ...],
) -> Tuple[List[Tensor], ...]:
    assert len(outputs) == len(output_nodes)
    output_grads = []
    for i, (output, output_node) in enumerate(zip(outputs, output_nodes)):
        node_grads = []
        for node_output in output_node.outputs:
            if i < len(grads) and node_output is output:
                node_grads.append(grads[i])
            elif node_output is output:
                node_grads.append(nura.oneslike(output))
            else:
                node_grads.append(nura.zeroslike(output))
        output_grads.append(node_grads)
    return tuple(output_grads)


def grad(
    outputs: Union[Tuple[Tensor, ...], Tensor],
    grads: Optional[Union[Tuple[Tensor, ...], Tensor]] = None,
    inputs: Optional[Union[Tuple[Tensor, ...], Tensor]] = None,
) -> Tuple[Tensor, ...]:
    raise NotImplemented


def _grad(
    input: Tuple[Tensor, ...], output: Tensor, grad: Optional[Tensor] = None
) -> Dict[Tensor, Tensor]:
    raise NotImplemented


def _tupify(input: Optional[Union[Tuple[Tensor, ...], Tensor]]) -> Tuple[Tensor, ...]:
    if input is None:
        return ()
    if isinstance(input, Tensor):
        return (input,)
    return input


def vjp(
    input: Union[Tuple[Tensor, ...], Tensor],
    vec: Tensor,
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tuple[Tensor, ...]]:

    input = _tupify(input)
    if err := _vjperr(input, vec):
        raise err
    input = tuple(t.mutated(usegrad=True, grad=None, leaf=True) for t in input)
    vec = vec.mutated(usegrad=False, grad=None)
    output, grads = _vjp(input, vec, f, *args, **kwargs)
    return output.mutated(usegrad=False, gradfn=None, leaf=True), grads


def _vjp(
    input: Tuple[Tensor, ...],
    vec: Tensor,
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tuple[Tensor, ...]]:
    if err := _vjperr(input, vec):
        raise err
    with nura.autograd(enabled=True, reverse=True, forward=False):
        output = f(*input, *args, **kwargs)
    inputmap = _grad(input, output, vec)
    return output, tuple(inputmap.values())


def _vjperr(input: Tuple[Tensor, ...], vec: Tensor) -> Optional[ValueError]:
    if not all(t.gradtensor for t in input):
        return ValueError(
            "One or more Tensors passed to argument 'input' cannot have their grads computed because they're not differentiable types"
        )
    if not vec.gradtensor:
        return ValueError(
            f"Expected Tensor passed to 'vec' to be a floating-point type, received {vec.dtype.name()}"
        )
    return None


def jvp(
    input: Union[Tuple[Tensor, ...], Tensor],
    vec: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    input = _tupify(input)
    vec = _tupify(vec)
    if err := _jvperr(input, vec):
        raise err
    gen = (v for v in vec)
    input = tuple(t.mutated(usegrad=True, grad=next(gen)) for t in input)
    output, grad = _jvp(input, f, *args, **kwargs)
    return output.mutated(usegrad=False, leaf=True), grad


def _jvp(
    input: Tuple[Tensor, ...],
    f: Callable[..., Tensor],
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:
    with nura.autograd(enabled=True, reverse=False, forward=True):
        output = f(*input, *args, **kwargs)
    assert output.grad is not None
    return output, output.grad


def _jvperr(input: Tuple[Tensor, ...], vec: Tuple[Tensor, ...]) -> Optional[ValueError]:
    if not all(t.gradtensor for t in input):
        return ValueError(
            "One or more Tensors passed to argument 'input' cannot have their grads computed because they're not differentiable types"
        )
    if not all(v.gradtensor for v in vec):
        return ValueError(
            "One or more Tensors passed to argument 'vec' cannot be used to compute jvp() because they're not a floating-point type"
        )
    return None


def jacrev(
    input: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    pos=0,
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    input = _tupify(input)
    if err := _jacerr(input):
        raise err
    input = tuple(t.mutated(usegrad=True, grad=None, leaf=True) for t in input)
    with nura.autograd(enabled=True, reverse=True, forward=False):
        output = f(*input, *args, **kwargs)
    tensor = input[pos]
    jac = getjac(tensor, output)
    perts = getperts(output)

    for row, pert in zip(np.ndindex(output.dim), perts):
        _, grads = _vjp(input, pert, f, *args, **kwargs)
        jacrow = grads[pos]
        slc = row + (...,)
        jac[slc] = jacrow
    return output, jac


def jacfwd(
    input: Union[Tuple[Tensor, ...], Tensor],
    f: Callable[..., Tensor],
    pos=0,
    *args,
    **kwargs,
) -> Tuple[Tensor, Tensor]:

    input = _tupify(input)
    if err := _jacerr(input):
        raise err
    with nura.autograd(enabled=False):
        output = f(*input, *args, **kwargs)
    tensor = input[pos]
    perts = getperts(tensor)
    jac = getjac(tensor, output)
    colinput = [
        t.mutated(usegrad=True, grad=nura.zeroslike(t)) if i != pos else t
        for i, t in enumerate(input)
    ]
    for col, pert in zip(np.ndindex(tensor.dim), perts):
        colinput[pos] = colinput[pos].mutated(usegrad=True, grad=pert)
        _, jaccol = _jvp(tuple(colinput), f, *args, **kwargs)
        slc = (...,) + col
        jac[slc] = jaccol
    return output, jac


def _jacerr(input: Tuple[Tensor, ...]) -> Optional[ValueError]:
    if not all(t.gradtensor for t in input):
        return ValueError(
            "Cannot compute Jacobian because one or more Tensors passed to 'input' are not a floating-point type"
        )
    return None


def getperts(tensor: Tensor) -> Generator[Tensor, None, None]:
    nelem, dim, dtype = tensor.nelem, tensor.dim, tensor.dtype
    perts = nura.zeros((nelem,) + dim).to(dtype)
    arange = np.arange(nelem)
    indices = np.unravel_index(arange, dim)
    slc = (arange,) + indices
    perts[slc] = 1.0
    return (perts[i] for i in range(nelem))


def getjac(tensor: Tensor, output: Tensor) -> Tensor:
    dim = output.dim + tensor.dim
    jac = nura.zeros(dim).to(output.dtype)
    return jac
