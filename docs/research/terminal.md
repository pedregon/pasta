# Terminal Emulation

## Pseudo Terminal

A pseudo terminal is a pair of virtual character devices that provide a bidirectional
communication channel. This pair is referred to as a pty.
One end of the channel is called the master; the other end is called the slave[^1]. The slave end may be
thought of as a cable that acts like a terminal. The purpose of a pseudo terminal is to provide a means to control
and interact with a terminal using software.

## Controlling Terminal

Typically, there are two methods for controlling a child process terminal with software: subprocess or fork.
For this capstone, the subprocess approach was chosen because of the benefits associated with an operating system
logical boundary versus process space.

### Raw Versus Cooked Mode

To wrap a subprocess such as `bash`, the parent program must use a pty. Assuming that the parent program 
standard input file descriptor is a TTY, it must be set into raw mode. Raw mode passes data from standard
input as-is to the program without interpreting any of the special characters, useful for TUIs.
The default mode for most REPLs is cooked, which preprocesses the input.

### Echo Mode

Echo mode is set on the slave file descriptor of the pty. Echo mode is what returns standard input to standard output
as one interacts with the shell. For example, each keystroke is replayed back to the standard ouput, even before the
command input has been submitted. For the purposes of this capstone, echo mode will remain on to mirror typial terminal
usage.

### Window Resizing

To prevent unexpected terminal output, a pty must consider the window resizing of the parent process. A parent program may resize the slave 
file decriptor window when the `SIGWICH` signal is detected by the parent. The parent may then utilize `termios` to adjust the subprocess
terminal attributes accordingly.

### Buffer Size

When reading output from the various file descriptors, it is important to set a buffer size to prevent data loss.

### Sending Signals

A pty is the controlling terminal, therefore signals read from the parent in raw mode are forwarded to the slave file descriptor. If the parent
software needs to send a signal to the pty, then it must send control signals using ANSI escape codes.

## Memory Pipes

In `python`, the subprocess standard output and standard error is best captured via in-memory pipes. In-memory pipes are one-way writable and readable.
A pty slave file descriptor acts like a terminal and thus is assigned to the standard input of the subprocess. The subprocess standard output and error
does not need to act like a terminal. Pipes are sufficient.

### Buffer Limitations

Unfortunately, in-memory pipes are limited to a parent process' memory. Memory is faster than disk read-write, but in a shell, data is streaming
continuously and sometimes eratic depending on the command executed. Therefore, files may be considered when buffer limitations are a concern. However,
for this capstone, memory limitations will not be consideredin an effort to not over-engineer the solution. A `reader` data structure will
be leveraged to differentiate the prompt and command lifecycles. The `reader` will read from the buffer while the buffer is replayed to the appropriate
standard ouput and standard error that the user expects, in an effort to prevent data loss for the user.

[^1]: https://man7.org/linux/man-pages/man7/pty.7.html