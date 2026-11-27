# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""REV-T6: how the Mega bridge cuts what arrives into lines."""
from r2_shadow_bridge.protocol import MAX_LINE, split_lines


def test_lines_cut_on_newline_or_carriage_return():
    lines, buf = split_lines(b"AUTO O", b"N\r\nTRACK OFF\nPAR")
    assert [x for x in lines if x] == [b"AUTO ON", b"TRACK OFF"]
    assert buf == b"PAR"


def test_noise_without_a_newline_is_thrown_away_and_the_next_line_counts():
    lines, buf = split_lines(b"", b"x" * 9000)
    assert lines == [] and buf == b""                      # over MAX_LINE: gone, not kept growing
    lines, buf = split_lines(buf, b"AUTO OFF\n")
    assert lines == [b"AUTO OFF"]


def test_a_long_but_allowed_line_is_kept():
    lines, buf = split_lines(b"", b"y" * MAX_LINE)
    assert buf == b"y" * MAX_LINE
