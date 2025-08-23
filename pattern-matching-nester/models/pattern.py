class Pattern():
    def __init__(self, pieces: list, seams: list):
        self.pieces = pieces
        self.seams = seams

    def __str__(self):
        return ";\n".join([str(x) for x in self.pieces]) if self.pieces else ""

    def find_seams_by_pair(self, part_1_name: str, part_2_name: str) -> list:
        affected_seams = []
        for seam in self.seams:
            if len(seam.seamparts) != 2:
                continue

            parts_in_seam = [x.part for x in seam.seamparts]
            if (part_1_name in parts_in_seam and part_2_name in parts_in_seam):
                affected_seams.append(seam)

        return affected_seams
