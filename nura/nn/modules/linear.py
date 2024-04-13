import nura.types as types
import nura.nn.functional as f
import nura.utils as utils
from nura.nn import Module, Parameter, parameter
from nura.tensors import Tensor
from nura.types import dtype
from typing import Type, Optional


class Linear(Module):

    def __init__(
        self,
        indim: int,
        outdim: int,
        bias=True,
        dtype: Optional[Type[dtype]] = None,
    ) -> None:
        super().__init__()
        if dtype is None:
            dtype = types.float
        self._indim = indim
        self._outdim = outdim
        self._dtype = dtype
        self._weight = parameter(utils.randn((outdim, indim)), dtype=dtype)
        self._bias = parameter(utils.randn(outdim), dtype=dtype) if bias else None

    @property
    def weight(self) -> Parameter:
        return self._weight

    @property
    def bias(self) -> Optional[Parameter]:
        return self._bias

    @property
    def indim(self) -> int:
        return self._indim

    @property
    def outdim(self) -> int:
        return self._outdim

    @property
    def dtype(self) -> Type[dtype]:
        return self._dtype

    def forward(self, x: Tensor) -> Tensor:
        return f.linear(x, self.weight, self.bias)

    def to(self, dtype: Type[types.dtype]) -> Module:
        mod = super().to(dtype)
        mod._dtype = dtype
        return mod

    def xrepr(self) -> str:
        indim, outdim = self.indim, self.outdim
        bias = True if self.bias is not None else False
        dtype = self.dtype.name()
        return f"{self.name()}({indim=} {outdim=} {bias=} {dtype=})"
