from pasta import pty, sessions


def test_pasta() -> None:
    pasta = pty.Pasta("")
    try:
        with pasta.spool() as typescript:
            state = sessions.State()
            for action in typescript.tokenize():
                print(action)
    finally:
        pasta.close()