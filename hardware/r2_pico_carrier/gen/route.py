"""Route r2_pico_carrier.kicad_pcb with Freerouting: export Specctra DSN, run Freerouting
without its window, import the session (tracks and vias), refill the GND pours, save.
Track widths come from the board's net classes (Power 0.5 mm, Default 0.25 mm).

    $KPY hardware/r2_pico_carrier/gen/route.py

Needs Java 21 and freerouting-2.5.0.jar (FREEROUTING, default ~/tools/freerouting-2.5.0.jar).
"""
import glob
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.normpath(os.path.join(HERE, "..", "r2_pico_carrier.kicad_pcb"))
JAR = os.environ.get("FREEROUTING", os.path.expanduser(r"~\tools\freerouting-2.5.0.jar"))
JAVA = os.environ.get("JAVA") or (sorted(glob.glob(r"C:\Program Files\Eclipse Adoptium\*\bin\java.exe")) or ["java"])[-1]


def main():
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):           # start from a clean board every time
        board.Remove(t)
    dsn, ses = PCB.replace(".kicad_pcb", ".dsn"), PCB.replace(".kicad_pcb", ".ses")
    if os.path.exists(ses):
        os.remove(ses)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("DSN export failed")
    cmd = [JAVA, "-jar", JAR, "-de", dsn, "-do", ses, "-mp", "100", "--gui.enabled=false"]
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print(r.stdout[-1500:], r.stderr[-1500:])
    if not os.path.exists(ses):
        sys.exit("Freerouting wrote no session")
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("SES import failed")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print("routed:", sum(1 for t in board.GetTracks()), "tracks and vias")


if __name__ == "__main__":
    main()
