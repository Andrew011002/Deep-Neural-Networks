from neuro.tensors import Tensor
from typing import Iterator, Optional, OrderedDict, Tuple, Any, Dict
from collections import OrderedDict
from neuro.utils import empty


class Parameter:

    def __init__(self, tensor: Optional[Tensor] = None) -> None:
        self._tensor: Tensor = (
            empty(0) if tensor is None else tensor.mutated(usegrad=True)
        )

    @property
    def tensor(self):
        return self._tensor

    def __repr__(self) -> str:
        return repr(self._tensor).replace("tensor", "param")


class Buffer:

    def __init__(self, tensor: Optional[Tensor] = None) -> None:
        self._tensor: Tensor = (
            empty(0) if tensor is None else tensor.mutated(usegrad=False)
        )

    @property
    def tensor(self):
        return self._tensor

    def __repr__(self) -> str:
        return repr(self._tensor).replace("tensor", "buff")


class Module:

    def __init__(self, *args, **kwargs) -> None:
        self._mods: OrderedDict[str, Optional["Module"]] = OrderedDict()
        self._params: OrderedDict[str, Optional[Parameter]] = OrderedDict()
        self._buffs: OrderedDict[str, Optional[Buffer]] = OrderedDict()
        self._active: bool = True

    @property
    def active(self):
        return self._active

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    def forward(self):
        raise NotImplemented

    def mods(self) -> Iterator[Tuple[str, Optional["Module"]]]:
        return iter((n, m) for n, m in self._mods.items())

    def params(self) -> Iterator[Tuple[str, Optional[Parameter]]]:
        return iter((n, p) for n, p in self._params.items())

    def buffs(self) -> Iterator[Tuple[str, Optional[Buffer]]]:
        return iter((n, b) for n, b in self._buffs.items())

    def allmods(self):
        pass

    def train(self):
        self._trainable = True
        return self

    def eval(self):
        self._trainable = False
        return self

    def __call__(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    def __setattr__(self, name, value):
        if isinstance(value, Module):
            self._mods[name.replace("_", "")] = value
            self.__dict__[name] = value
        elif isinstance(value, Parameter):
            self._params[name.replace("_", "")] = value
            self.__dict__[name] = value
        elif isinstance(value, Buffer):
            self._buffs[name.replace("_", "")] = value
            self.__dict__[name] = value
        else:
            names = {"_mods", "_params", "_buffs", "_active", "_args", "_kwargs"}
            assert name in names, f"invalid attr: {name}"
            self.__dict__[name] = value

    def __repr__(self) -> str:
        return self.__class__.__name__
