import nura
import nura.nn as nn
import nura.nn.functional as f
import numpy as np


def main():
    x = np.random.randn(10)
    z = nura.tensor(x, usegrad=True, dtype=nura.float)
    a = f.softmax(z)
    a.backward(nura.oneslike(a))
    print(z.grad)


if __name__ == "__main__":
    main()
