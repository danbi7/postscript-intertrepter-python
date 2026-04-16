# PostScript Interpreter (CptS 355)

## Overview
This project is a PostScript interpreter implemented in Python, based on concepts and partial implementation from CptS 355 (Programming Language Design) lecture videos by Professor Subu Kandaswamy. The initial structure and some components were provided in the lectures, and the remaining functionality was completed as part of this implementation.

The interpreter supports both **static scoping** and **dynamic scoping**, along with a range of core PostScript operations.

---

## Features

### Scoping Modes
- Static Scoping
- Dynamic Scoping

---

## Supported Commands

### Stack Operations
- `exch`
- `pop`
- `copy`
- `dup`
- `clear`
- `count`

### Arithmetic
- `sub`
- `div`
- `idiv`
- `mod`
- `abs`
- `neg`
- `ceiling`
- `floor`
- `round`
- `sqrt`

### Dictionary Operations
- `length`
- `maxlength`

### String Operations
- `length`
- `get`
- `getinterval`
- `putinterval`
- String literal parsing using `( ... )`

### Boolean Operations
- `eq`
- `ne`
- `ge`
- `gt`
- `le`
- `lt`
- `and`
- `or`
- `not`
- `true`
- `false`

### Flow Control
- `if`
- `ifelse`
- `for`
- `repeat`

### I/O
- `print`
- `=`
- `==`

---

## Setup and Installation

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

4. Install dependencies:
   ```bash
   pip install pytest

## Running the Interpreter

Start the interactive REPL:
   ```bash
   python3 psip.py
   ```

## Running Tests

Execute the test suite using:
   ```bash
   pytest psip_test.py
