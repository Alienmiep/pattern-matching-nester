class Pattern():
    def __init__(self, pieces: list):
        self.pieces = pieces

    def __str__(self):
        return ";\n".join([str(x) for x in self.pieces])
