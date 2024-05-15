import nura
import nura.types as types
from nura.types import Tensorlike, Scalar, dtype, dim, dimlike
from typing import Optional, Tuple, Type, Any, Union, List, Self, TYPE_CHECKING
from numpy import ndarray

if TYPE_CHECKING:
    from nura.autograd.graph import Node


class Tensor:

    def __init__(
        self,
        data: ndarray,
        usegrad: bool,
        grad: Optional["Tensor"],
        gradfn: Optional["Node"],
        leaf: bool,
    ) -> None:
        self._data: ndarray = data
        self._grad: Optional[Tensor] = grad
        self._gradfn: Optional[Node] = gradfn
        self._usegrad: bool = usegrad
        self._leaf: bool = leaf
        self._version: int = 0

    @property
    def data(self) -> ndarray:
        return self._data

    @property
    def dim(self) -> dim:
        return self._data.shape

    @property
    def ndim(self) -> int:
        return self._data.ndim

    @property
    def nelem(self) -> int:
        return self._data.size

    @property
    def usegrad(self) -> bool:
        return self._usegrad

    @property
    def grad(self) -> Optional["Tensor"]:
        return self._grad

    @property
    def gradfn(self) -> Optional["Node"]:
        return self._gradfn

    @property
    def leaf(self) -> bool:
        return self._leaf

    @property
    def version(self) -> int:
        return self._version

    @property
    def dtype(self) -> Type[dtype]:
        return types.dtypeof(self.data)

    @property
    def gradtensor(self) -> bool:
        return self.dtype in (types.half, types.float, types.double)

    @property
    def T(self) -> "Tensor":
        dim = tuple(range(self.ndim - 1, -1, -1))
        return self.permute(dim)

    def item(self) -> Scalar:
        return nura.item(self)

    def list(self) -> List[Any]:
        return self.data.tolist()

    def backward(
        self, grad: Optional["Tensor"] = None, input: Optional["Tensor"] = None
    ) -> None:
        nura.backward(self, grad, input)

    def cleargrad(self) -> None:
        self._grad = None

    def clearedgrad(self) -> "Tensor":
        cls = type(self)
        return cls(self.data, self.usegrad, None, self.gradfn, self.leaf)

    def zerograd(self) -> None:
        self._grad = nura.zeroslike(self)

    def zeroedgrad(self) -> "Tensor":
        cls = type(self)
        return cls(self.data, self.usegrad, nura.zeroslike(self), self.gradfn, True)

    def retain(self) -> None:
        if self.gradfn is None:
            raise ValueError("Tensor has no gradient function to retain gradient")
        self.gradfn._retain = True

    def unretain(self) -> None:
        if self.gradfn is None:
            raise ValueError("Tensor has no gradient function to unretain gradient")
        self.gradfn._retain = False

    def attach(self) -> None:
        self._usegrad = True

    def attached(self) -> "Tensor":
        cls = type(self)
        return cls(self.data, True, self.grad, self.gradfn, self.leaf)

    def detach(self) -> None:
        self._usegrad = False
        if self._gradfn is not None:
            self._gradfn._retain = False
            self._gradfn = None

    def detached(self) -> "Tensor":
        cls = type(self)
        t = cls(self.data, False, None, None, True)
        return t

    def mutate(self, **attrs: Any) -> None:
        for k, v in attrs.items():
            setattr(self, f"_{k}", v)

    def mutated(self, **attrs: Any) -> "Tensor":
        cls = type(self)
        t = cls(self.data, self.usegrad, self.grad, self.gradfn, self.leaf)
        for k, v in attrs.items():
            setattr(t, f"_{k}", v)
        return t

    def clone(self) -> "Tensor":
        return nura.clone(self)

    def contiguous(self) -> "Tensor":
        return nura.tocontiguous(self)

    def dot(self, other: "Tensor") -> "Tensor":
        return nura.dot(self, other)

    def square(self) -> "Tensor":
        return nura.square(self)

    def sqrt(self) -> "Tensor":
        return nura.sqrt(self)

    def exp(self) -> "Tensor":
        return nura.exp(self)

    def log(self) -> "Tensor":
        return nura.log(self)

    def sin(self) -> "Tensor":
        return nura.sin(self)

    def cos(self) -> "Tensor":
        return nura.cos(self)

    def sum(self, dim: Optional[dimlike] = None, keepdims: bool = False) -> "Tensor":
        return nura.sum(self, dim, keepdims)

    def max(self, dim: Optional[dimlike] = None, keepdims: bool = False) -> "Tensor":
        return nura.max(self, dim, keepdims)

    def min(self, dim: Optional[dimlike] = None, keepdims: bool = False) -> "Tensor":
        return nura.min(self, dim, keepdims)

    def squeeze(self, dim: Optional[dimlike] = None) -> "Tensor":
        return nura.squeeze(self, dim)

    def unsqueeze(self, dim: dimlike) -> "Tensor":
        return nura.unsqueeze(self, dim)

    def reshape(self, newdim: types.dim) -> "Tensor":
        return nura.reshape(self, newdim)

    def transpose(self, dim0: int = -2, dim1: int = -1) -> "Tensor":
        return nura.transpose(self, dim0, dim1)

    def permute(self, dims: types.dim) -> "Tensor":
        return nura.permute(self, dims)

    def abs(self) -> "Tensor":
        return nura.abs(self)

    def any(self, dim: Optional[dimlike] = None, keepdims: bool = False) -> "Tensor":
        return nura.tensorany(self, dim, keepdims)

    def all(self, dim: Optional[dimlike] = None, keepdims: bool = False) -> "Tensor":
        return nura.tensorall(self, dim, keepdims)

    def __add__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.add(self, other)

    def __radd__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.add(self, other)

    def __iadd__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.iadd(self, other)
        return self

    def __sub__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.sub(self, other)

    def __rsub__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.sub(tensor(other, dtype=self.dtype), self)

    def __isub__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.isub(self, other)
        return self

    def __mul__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.mul(self, other)

    def __rmul__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.mul(self, other)

    def __imul__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.imul(self, other)
        return self

    def __truediv__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.div(self, other)

    def __rtruediv__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.div(tensor(other, dtype=self.dtype), self)

    def __itruediv__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.idiv(self, other)
        return self

    def __floordiv__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.floordiv(self, other)

    def __rfloordiv__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.floordiv(tensor(other, dtype=self.dtype), self)

    def __ifloordiv__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.ifloordiv(self, other)
        return self

    def __mod__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.modulo(self, other)

    def __rmod__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.modulo(tensor(other, dtype=self.dtype), self)

    def __imod__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.imodulo(self, other)
        return self

    def __matmul__(self, other: "Tensor") -> "Tensor":
        return nura.matmul(self, other)

    def __imatmul__(self, other: "Tensor") -> Self:
        nura.imatmul(self, other)
        return self

    def __pow__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.pow(self, other)

    def __rpow__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.pow(tensor(other, dtype=self.dtype), self)

    def __ipow__(self, other: Union["Tensor", Scalar]) -> Self:
        nura.ipow(self, other)
        return self

    def __pos__(self) -> "Tensor":
        return nura.pos(self)

    def __neg__(self) -> "Tensor":
        return nura.neg(self)

    def __abs__(self) -> "Tensor":
        return nura.abs(self)

    def __invert__(self) -> "Tensor":
        return nura.tensornot(self)

    def __eq__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.equal(self, other)

    def __lt__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.less(self, other)

    def __le__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.lessequal(self, other)

    def __gt__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.greater(self, other)

    def __ge__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.greaterequal(self, other)

    def __ne__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.notequal(self, other)

    def __hash__(self) -> int:
        return nura.hashtensor(self)

    def __len__(self) -> int:
        return len(self.data)

    def __bool__(self) -> None:
        raise ValueError(
            "Truth of Tensor is undefined for more than one element, use any() or all()"
        )

    def __and__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.tensorand(self, other)

    def __or__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.tensoror(self, other)

    def __xor__(self, other: Union["Tensor", Scalar]) -> "Tensor":
        return nura.tensorxor(self, other)

    def to(self, dtype: Type[types.dtype]) -> "Tensor":
        return nura.to(self, dtype)

    def byte(self) -> "Tensor":
        return self.to(types.byte)

    def char(self) -> "Tensor":
        return self.to(types.char)

    def short(self) -> "Tensor":
        return self.to(types.short)

    def int(self) -> "Tensor":
        return self.to(types.int)

    def long(self) -> "Tensor":
        return self.to(types.long)

    def half(self) -> "Tensor":
        return self.to(types.half)

    def float(self) -> "Tensor":
        return self.to(types.float)

    def double(self) -> "Tensor":
        return self.to(types.double)

    def bool(self) -> "Tensor":
        return self.to(types.bool)

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in ("_data", "_usegrad", "_grad", "_gradfn", "_leaf", "_version"):
            raise AttributeError(f"{name} cannot be assigned to {nura.typename(self)}")
        if name == "_usegrad" and value and not self.gradtensor:
            raise ValueError(
                f"Only floating-point tensors can use gradient, received {dtype.name()}"
            )
        if name == "_data" and "_version" in self.__dict__ and self._usegrad:
            self._version += 1
        self.__dict__[name] = value

    def __getitem__(self, slice_: Union[Tensorlike, "Tensor", slice]) -> "Tensor":
        return nura.select(self, slice_)

    def __setitem__(self, slice_: Any, item: Any) -> None:
        if isinstance(slice_, tuple):
            slice_ = tuple(i.data if isinstance(i, Tensor) else i for i in slice_)
        if isinstance(slice_, Tensor):
            slice_ = slice_.data
        if isinstance(item, Tensor):
            item = item.data
        self.data[slice_] = item

    def __repr__(self) -> str:
        s = repr(self._data).replace("array(", "").replace(",", "").replace(")", "")
        if " dtype" in s:
            i = s.index(" dtype")
            s = s[:i]
        if nura.Autograd.forwardmode():
            r = ["Primal(", s]
        else:
            r = ["Tensor(", s]
            if self.usegrad:
                gradfn = self.gradfn.name() if self.gradfn is not None else None
                r.append(f" {gradfn=}")
        dtype = self.dtype.name()
        r.append(f" {dtype=})")
        return "".join(r)


def tensor(
    data: Union[Tensor, Tensorlike],
    usegrad: bool = False,
    dtype: Optional[Type[dtype]] = None,
) -> Tensor:
    if isinstance(data, Tensor):
        dtype = data.dtype
        data = data.data.copy()
    if dtype is None:
        dtype = nura.dtypeof(data)
    data = dtype.numpy(data)
    return Tensor(data, usegrad, None, None, True)
