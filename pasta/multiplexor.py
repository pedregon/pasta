import subprocess


class Terminal:
    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc