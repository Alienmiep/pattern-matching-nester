class Pattern():
    def __init__(self, pieces: list, seams: list):
        self.pieces = pieces
        self.seams = seams

    def __str__(self):
        return ";\n".join([str(x) for x in self.pieces]) if self.pieces else ""

    def find_seams_by_pair(self, part_1_full_name: str, part_2_full_name: str) -> list:
        part_1_names = part_1_full_name.split("+")
        part_2_names = part_2_full_name.split("+")

        affected_seams = []
        for seam in self.seams:
            if len(seam.seamparts) != 2:
                continue
            parts_in_seam = [x.part for x in seam.seamparts]
            if (parts_in_seam[0] in part_1_names and parts_in_seam[1] in part_2_names) \
                or (parts_in_seam[0] in part_2_names and parts_in_seam[1] in part_1_names):
                affected_seams.append(seam)

        return affected_seams
