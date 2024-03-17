import subprocess


class Pasta:
    def __init__(self, proc: subprocess.Popen) -> None:
        self.proc = proc
