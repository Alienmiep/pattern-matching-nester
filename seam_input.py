import os

def get_input(label):
    return input(f"Enter value for {label}: ")

def create_seam_entry(values):
    return f"""<seam>
  <id>{values['id']}</id>
  <seampart>
    <part>{values['part_a']}</part>
    <start>{values['start_a']}</start>
    <end>{values['end_a']}</end>
    <direction>{values['direction_a']}</direction>
  </seampart>
  <seampart>
    <part>{values['part_b']}</part>
    <start>{values['start_b']}</start>
    <end>{values['end_b']}</end>
    <direction>{values['direction_b']}</direction>
  </seampart>
</seam>\n"""

def main():
    filename = "seams.txt"
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            pass  # Just create the file

    keys = ['id', 'part_a', 'start_a', 'end_a', 'direction_a', 'part_b', 'start_b', 'end_b', 'direction_b']
    values = {key: get_input(key) for key in keys}
    entry = create_seam_entry(values)
    with open(filename, 'a') as f:
        f.write(entry)
    print("Seam entry added successfully.")

if __name__ == "__main__":
    main()
