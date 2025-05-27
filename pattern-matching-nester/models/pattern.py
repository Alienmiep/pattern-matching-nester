class Pattern():
    def __init__(self, pieces: list, seams: list):
        self.pieces = pieces
        self.seams = seams

    def __str__(self):
        return ";\n".join([str(x) for x in self.pieces]) if self.pieces else ""
