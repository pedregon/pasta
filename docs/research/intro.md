# Introduction

## Background

Have you been in a capture-the-flag event and had to use a chat channel to share proof of concepts for challenges?
Teammates are messaging back and forth. Tool output is splatted across the chat and you just want to know what goes
with what. How about your writeup notes? Note taking in offensive cyber security is paramount to
your success, but often times notes suffer one of two problems: someones art or time decay.

Taking a step a back, writeups typically serve as the post-analysis deliverable for organizations conducting an engagement. 
Let's assume that we take good notes. As an offensive security organization, our goal is provide effective services to our customers, but how
do we augment our capabilities or progress our workflows? Introducing feedback loops or the ability to query and analyze engagements over time could be powerful.
Is automation the answer? Probably not, maybe AI is? Unfortunately, attack data is too dynamic, TTPs are not standardized, and circumstantial 
data is prevelant for the data management solutions that exist today.
Designing and building these solutions or baking them into C&Cs requires significant finanical investment and comes with the challenges associated with
an evolving Internet. Also, attack data presentation, how an ethical hacker interacts with the engagement data akin to their workflows, is often not considered
or a disciplinary gap exists between the developers and end users of these systems.

In a nutshell, a lack of observability within an engagement leads to trickle-down miscommunication. If the red team is inefficient during an
engagement because they cannot collaborate effectively or if the blue team does not fully understand the writeup, then we have problems.

### Layman's Terminology

For the purposes of this research, offensive cyber security may be summarized by two security assurance process.
A [penetration test](https://www.eccouncil.org/cybersecurity/what-is-penetration-testing/) is a simulated attack
used to identify organizational vulnerabilities and inform cyber security policy.
Red teaming goes a step beyond a penetration test. A [red team](https://www.crowdstrike.com/cybersecurity-101/red-teaming/)
engagement uses ethical hacking to emulate an adversary attempting to breach an organization's security posture.

## Problem Statement

So where does this leave us? In a red team, how do we improve observability of the "adversary" and analyze that data? Well, hacking leverage tools.
There are N post-processors out there for each X tool. Unfortunately, the tool decides how to collect the data, what format to use, and the capabilities involved.
In engagements, ethical hackers do not control their available targets and may encounter unforseen network logic. Hacking can be weird. A dynamic workflow creates
challenges for observability and managing that data.
Developing a post-processor for some tool, which you may not control, often yields endless edge cases for an organization data standard.

### Proposed Solution

This project seeks to start with the *collection of data* rather than *reacting to the collected data first*.
The lexical analysis of interactive shell data would introduce engagement context into post-processing, resulting in a more effective presentation of
attack data. Interactive shell data is atomic to tool output. Much of ethical hacking consitutes the use of a terminal to execute TTPs.
This is not exhaustive, but for the purposes of scope, we will ignore other ethical hacking "sources" such as a web browser or other GUI.

### Justification

By applying lexical analysis onto interactive shell data, we improve the quality of the observed data. Data quality is critical to solving the aforementioned downstream
attack data presentation challenges. Understanding the context of the ethical hacker's actions would inform post-processors of what to look for and drive their
automation. One could even develop a language server for notetaking that standardizes organization data. No matter what observability management solution is leveraged,
human interaction will remain integral to cleaning any collected data. AI applications are another example.
Imagine if you could talk to your commands or writeup notes during an engagement?

The proposed solution also copes with the fact that many of the tools used within an engagement are not controlled
by the red team's data standards. The observability mechanism is tool agnostic. Therefore, there are no operational security concerns at play because the red team
is not installing additional indicators onto a target. Often times, a red team does not want to be caught for the sake of the engagement effectiveness.

In summary, there are many capabilities that an organization could
produce if the data ingested was tokenized.

### Project Challenge

If collecting data from a shell is the answer, can we not just use a terminal emulator recorder? Unfortunately, existing terminal emulator recorders do not distinguish
a parent shell from a child shell, the [subshell problem](subshell.md). The purpose of this project is to solve the subshell problem such that lexical analysis
may be applied to the network and not just the origin. Some tools such as Metasploit might offer spool capabilities but do not event consider the remote shell.
Also, most of the existing terminal emulator records do not differentiate command input from command output.

## Understanding the Red Team Workflow

Knowledge often gets lost in translation within a red team
during an engagement and from the red team to the blue team
when describing TTPs used. This section will present the ideas that led
to the identification of the proposed solution. The cyber security industry
overlooks or does not have consensus when it comes to modeling the red
team workflow. Blue team governance and post-analysis models dominant the field.
However, when trying to build red team data observability solutions you are left with trying
to fit a square peg into a round hole with blue team models of the adversary.

### Strengths of Models

- Effectively reduce misunderstanding and miscommunications.
- Understand attacker motivations and patterns to better prioritize defenses, allocate
resources, inform policies, and develop incident response plans.

### Weaknesses of Models

- Simplified representations of complex systems are subject to loss of detail.
- Disciplinary assumptions, limited scope, and finite predictive ability.

### Well-Known Models

[Unified Kill Chain](https://www.unifiedkillchain.com/)

:   Kill chains outline the phased progressions of an attacker toward their goals:
    in, through, and out.

[ATT&CK Framework](https://attack.mitre.org/)

:   Matrixes categorize TTPs from each phase and map them to general threat objectives.

[Diamond Model](https://www.activeresponse.org/wp-content/uploads/2013/07/diamond.pdf)

:   Identifying the relationships within an intrusion to better understand attacker motivations;
    an adversary deploys a capability over some infrastructure against a victim.

### Adversarial Decision Making

The adversarial decision making model (ADMM) is a feedback loop that models the atomic thought process
of a hacker. There is nothing special about the ADMM, as it is similar
to other decision making models such as the
[OODA Loop](https://www.oodaloop.com/the-ooda-loop-explained-the-real-story-about-the-ultimate-model-for-decision-making-in-competitive-environments/).
The ADMM was designed to highlight the points of friction that a hacker would encounter during an interactive engagement.
Other industry models emphasize post analysis focused on the blue team whereas the ADMM considers the engagement workflow that ultimately
led to the post analysis story.

**ADDM**

![Adversarial Decision Making Model](../img/admm.drawio.svg)

Each block in the diagram, stage in the data lifecycle, has a protruding arrow that is a point of friction within an
engagement. If you were to consider a cyber kill chain, this ADMM process would be a sub loop within each phase.

*TTPs*

:  Tools, techniques, and procedures.

*Execute*

:  Action or use of a TTP.

*Response*

:  Feedback from the TTP action.

*Interpret*

:  Interpretation of the feedback or TTP output into attack data.

*Artifacts*

:  Attack data and aditional knowledge learned.

*Analyze & Decide*

:  Based on analysis of situation presented by artifacts, determine the next TTP to use to accomplish the objectives.

The lexical analysis of interactive shell data solution fits into the Response to Interpret point of friction within the ADMM.
The semantic analysis of this data would be better encompassed by Interpret to Artifacts.