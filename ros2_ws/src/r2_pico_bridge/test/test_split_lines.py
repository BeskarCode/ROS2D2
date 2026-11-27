# ROS2D2, created by NandoMadrid (https://www.astromechspain.com/droides/r2-d2-nandomadrid/) · Astromech Spain (https://www.astromechspain.com)
"""REV-T6: how the Pico bridge cuts what arrives into lines."""
from r2_pico_bridge.protocol import MAX_LINE, split_lines


def test_lines_cut_on_newline_carriage_returns_dropped():
    lines, buf = split_lines(b"R 0:4", b"20\r\nHB 100 O\r\nR")
    assert lines == [b"R 0:420", b"HB 100 O"]
    assert buf == b"R"


def test_noise_without_a_newline_is_thrown_away_and_the_next_line_counts():
    # the 8 kB limit itself: without it the buffer would keep the 9000 bytes and glue them to the next line
    lines, buf = split_lines(b"", b"x" * 9000)
    assert lines == [] and buf == b""
    lines, buf = split_lines(buf, b"R 0:420\n")
    assert lines == [b"R 0:420"]


def test_a_long_but_allowed_line_is_kept():
    assert split_lines(b"", b"y" * MAX_LINE)[1] == b"y" * MAX_LINE
