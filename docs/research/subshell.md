# Subshell Problem

The subshell problem is a limitation of terminal recorders to distinguish shell data of a child shell 
from a parent shell. This requires significant human review of terminal recording output, including
scripted windows. Ethical hackers use *many* tools to spawn shells and chain or tape these shells
together. This results in endless edge cases that often makes developers develop a post processor
per tool, infeasible in an ever-evolving cyber domain.

## Interactive Shell Data

Interactive shell data is an ADMM Action and Response pair encompassing the following terminal data lifecycles.

### Prompt Lifecycle

The prompt lifecycle distinguishes one command from another. This is the foundation of shell processing.
When the shell prompt shows up, one knows that the previous command
has concluded.

### Command Lifecycle

The command lifecycle distinguishes command input from command output. For example,
when a command such as `nmap` is executed, the command input differs from the command output.
Differentiating the two empowers command output parsing and metrics across engagements.

### Shell Lifecycle

The shell lifecycle distinguishes a child shell from a parent shell. For example, a parent shell may be
a local `bash` session and the child shell a remote `ssh` session.

## A Tour of Terminal Recorders

### Scripted Windows

The Linux `script` command is often used to capture raw terminal output by spawning a pty and writing the observed
data to a `typescript` file. There are various utilities to playback the captured input and output, but the program
makes no effort to differentiate the data.

### Shell Hooks

Shell hooks provide scripts the ability to register callbacks on shell events. Notably, `zsh` includes widgets but
shell hooks are limited to a process lifecycle. Hooks may differentiate command input and output via some shell magic,
but do not have an understanding of the contents until the process completes. Therefore, shell hooks are limited when
a process hangs and cannot detect remote commands.

The shell history is a hook capability, but only captures command input.
The `atuin` program is an example shell hook tool.

### Asciinema

The `asciinema` tool is a popular terminal recorder that acts similar to scripted windows. The tool includes
the `asciicast/v2` data standard for recording output instead of `typescript`. The `asciicast/v2` standard does
differentiate prompts but does yet separate command input from command output.

### Readline Wrappers

Readline is a Linux library that differentiates the prompt. Tools such as `rlwrap` even differentiate command input
and output, but like most ptys, it does not understand that child shell data is different from the orginial process.

### Terminal Multiplexors

Terminal multiplexors manage many ptys typically via a client-server protocol. Popular tools such as `tmux`, `screen`,
and `zellij` use commands to interact with their respective servers. Notably, `tmux` includes a control mode
capability intended to provide an interface for `iterm2`. Unfortuately, control mode is limited by the same pty
problems that readline has. The `tmux` tool can track layout changes, commands, and shell data, but only
for the local machine that it is installed on, not subshells.

### eBPF Monitoring

Linux includes a kernel-level sandbox called `eBPF` for monitoring system calls, network activity, and other operating system
capabilities. The `eBPF` ecosystem leverages compiled-byte code scripts that are often generated from higher
level programming languages. The capabilities offered are very powerful. Unfortuately, even with tools such as
`nhi` and `bcc`, the differentiating child shells from parent shells remains an issue.

### Ethical Hacking Tools

Often times information security tools include a means of recording the session or maintaining command history.
Tools that install implants or manage reverse shells typically do not even consider recording the subshell
data. The `metasploit` Ruby API and spool command do not include a utility to capture subshell data. Nevertheless,
subshells within these shells would also not be recorded. Some tools such as `X` record shell activity on each
implant and communicate back to the C&C, but this requires control of remote system as well as an installation
on disk or in-memory of the target, an OPSEC concern.

### Warp Terminal and AI

The `warp` terminal is built to leverage AI capabilities.
Again, AI is only as effective as the quality of input data. Tokenizing shell
data augments the data with better context.