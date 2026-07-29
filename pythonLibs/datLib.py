import numpy as np
import time

# class that allows for reading and writing of 2D array data to a file that can be read by OpenSCAD surface function
# is also used to store the DTM in assets
class datFile():
    # create class from array
    def __init__(self, arr : np.array):
        if(len(arr.shape) != 2):
            raise IOError("datFile object arr must be 2 dimesional")
        self.arr : np.array = arr

    # create class from file (using filename)
    @classmethod
    def fromFile(cls, fname : str):
        with open(fname, "r") as f:
            _, x, y = f.readline().split()
            x = int(x)
            y = int(y)
            cls.arr = np.zeros([x, y], np.uint16)
            for i in range(0, x):
                row = list(map(int, f.readline().split()))
                if(len(row) != y):
                    raise "incorrect number of entries in file"
                cls.arr[i] = np.asarray(row)
        return cls

    # write object to file
    def write(self, fname : str):
        with open(fname, "w+") as f:
            f.write(f"# {self.arr.shape[0]} {self.arr.shape[1]}\n")
            for line in self.arr:
                f.write(" ".join(np.char.mod('%d', line)))
                f.write("\n")


# the one unit "test" I have
# just used during development for testing that the files work correctly
if __name__ == "__main__":
    print("running tests for datLib")
    d = datFile(np.zeros([2000,2000], dtype=np.float16))
    print("loaded")

    n = 1000
    c = 0
    for _ in range(0, n):
        start = time.time()
        d.write("test.dat")
        c += time.time() - start

    print(f"for writing: over {n} itteration, average time is {c/n} seconds")

    c = 0
    for _ in range(0, n):
        start = time.time()
        d = datFile.fromFile("test.dat")
        c += time.time() - start
    
    print(f"for reading: over {n} itteration, average time is {c/n} seconds")

