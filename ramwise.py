"""
Ramwise start file.

    python ramwise.py            opens the window app
    python ramwise.py --top 20   any option runs the terminal version instead (see cli.py)
"""

import sys

if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args != ["--gui"]:
        import cli
        cli.main([a for a in args if a != "--cli"])
    else:
        import gui
        gui.main()
