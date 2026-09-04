# Jarvis Assistant

A personal AI assistant that can read files, run shell commands, and reason
about your local environment through Claude's tool-calling API. This is
Phase 1: a text-only "brain" with a small set of real tools. Voice, a
permission/audit system, and more capabilities come in later phases.

## Why this exists

Most "build your own JARVIS" projects stop at "chatbot that talks back."
The interesting engineering problem is the **tool-calling loop**: giving an
LLM the ability to take real actions on your machine, safely. That loop is
the core of this repo.

## Architecture