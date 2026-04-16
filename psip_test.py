"""
Test suite for psip.py - PostScript Interpreter in Python
Run with: pytest test_psip.py -v
"""
import pytest
import math
import psip


# -------------------------------------------------------------------------------------
# Helpers to reset gloabl state between tests
# -------------------------------------------------------------------------------------
def reset():
    psip.op_stack.clear()
    # Keep only the built-in dicitonary (index 0)
    while len(psip.dict_stack) > 1:
        psip.dict_stack.pop()
    psip.STATIC_SCOPING = False

def run(*tokens):
    reset()
    # Feed a sequence of tokens into process_input and return the stack
    for t in tokens:
        psip.process_input(t)
    return psip.op_stack

def stack():
    return psip.op_stack[:]


# -------------------------------------------------------------------------------------
# PARSERS
# -------------------------------------------------------------------------------------
class TestBooleanParsing:
    def test_parse_true(self):
        assert psip.process_boolean("true") is True

    def test_parse_false(self):
        assert psip.process_boolean("false") is False

    def test_parse_exception(self):
        with pytest.raises(psip.ParseFailed):
            psip.process_boolean("something")


class TestNumberParsing:
    def test_integer(self):
        assert psip.process_number("42") == 42
        assert isinstance(psip.process_number("42"), int)

    def test_float(self):
        assert psip.process_number("3.14") == pytest.approx(3.14)
        assert isinstance(psip.process_number("3.14"), float)

    def test_negative(self):
        assert psip.process_number("-7") == -7

    def test_invalid(self):
        with pytest.raises(psip.ParseFailed):
            psip.process_number("abc")
     

class TestNameConstantParsing:
    def test_valid(self):
        assert psip.process_name_constant("/foo") == "/foo"

    def test_invalid(self):
        with pytest.raises(psip.ParseFailed):
            psip.process_name_constant("foo")


class TestCodeBlockParsing:
    def test_simple(self):
        result = psip.process_code_block("{ 1 add }")
        assert result == ["1", "add"]

    def test_empty_block(self):
        result = psip.process_code_block("{}")
        assert result == []

    def test_nested(self):
        result = psip.process_code_block("{ { 1 } repeat }")
        assert "{ 1 }" in result

    def test_invalid(self):
        with pytest.raises(psip.ParseFailed):
            psip.process_code_block("not a block")


class TestStringLiteralParsing:
    def test_simple(self):
        assert psip.process_string_literal("(hello)") == "hello"

    def test_with_spaces(self):
        assert psip.process_string_literal("(hello world)") == "hello world"

    def test_invalid(self):
        with pytest.raises(psip.ParseFailed):
            psip.process_string_literal("hello")


# -------------------------------------------------------------------------------------
# STACK MANIPULATION
# -------------------------------------------------------------------------------------
class TestStackOps:
    def test_exch(self):
        run("1", "2", "exch")
        assert psip.op_stack[-2:] == [2, 1]

    def test_pop(self):
        run("1", "2", "pop")
        assert psip.op_stack == [1]

    def test_dup(self):
        run("5", "dup")
        assert psip.op_stack == [5, 5]

    def test_copy(self):
        run("1", "2", "3", "2", "copy")
        # Copies top 2: stack becomes [1, 2, 3, 2, 3]
        assert psip.op_stack == [1, 2, 3, 2, 3]

    def test_clear(self):
        run("1", "2", "3", "clear")
        assert psip.op_stack == []

    def test_count(self):
        run("1", "2", "3", "count")
        assert psip.op_stack[-1] == 3

    def test_count_empty(self):
        run("count")
        assert psip.op_stack[-1] == 0


# -------------------------------------------------------------------------------------
# ARITHMETIC
# -------------------------------------------------------------------------------------
class TestArithmetic:
    def test_add(self):
        assert run("3", "4", "add")[-1] == 7

    def test_add_float(self):
        assert run("1.5", "2.5", "add")[-1] == pytest.approx(4.0)

    def test_sub(self):
        assert run("10", "3", "sub")[-1] == 7

    def test_mul(self):
        assert run("3", "4", "mul")[-1] == 12

    def test_div(self):
        assert run("7", "2", "div")[-1] == pytest.approx(3.5)

    def test_idiv(self):
        assert run("7", "2", "idiv")[-1] == 3

    def test_idiv_truncates_toward_zero(self):
        assert run("-7", "2", "idiv")[-1] == -3

    def test_mod(self):
        assert run("10", "3", "mod")[-1] == 1

    def test_abs_positive(self):
        assert run("5", "abs")[-1] == 5

    def test_abs_negative(self):
        assert run("-5", "abs")[-1] == 5

    def test_neg(self):
        assert run("3", "neg")[-1] == -3

    def test_ceiling(self):
        assert run("3.2", "ceiling")[-1] == 4.0
        assert run("-4.8", "ceiling")[-1] == -4.0

    def test_floor(self):
        assert run("3.2", "floor")[-1] == 3.0
        assert run("-4.8", "floor")[-1] == -5.0

    def test_round(self):
        assert run("3.5", "round")[-1] == 4.0
        assert run("3.4", "round")[-1] == 3.0

    def test_sqrt(self):
        assert run("9", "sqrt")[-1] == pytest.approx(3.0)

    def test_div_by_zero(self):
        reset()
        psip.op_stack.extend([4, 0])
        with pytest.raises(psip.TypeMismatch):
            psip.div_operation()


# -------------------------------------------------------------------------------------
# DICTIONARY
# -------------------------------------------------------------------------------------
class TestDictionary:
    def test_def_and_lookup(self):
        run("/x", "42", "def", "x")
        assert psip.op_stack[-1] == 42

    def test_dict_creates_dict(self):
        run("5", "dict")
        assert isinstance(psip.op_stack[-1], psip.PSDict)

    def test_dict_capacity(self):
        run("5", "dict")
        d = psip.op_stack[-1]
        assert d.maxlength() == 5

    def test_begin_end(self):
        run("5", "dict", "begin")
        assert len(psip.dict_stack) == 2
        psip.process_input("end")
        assert len(psip.dict_stack) == 1

    def test_length_dict(self):
        run("5", "dict", "dup", "begin",
            "/a", "1", "def",
            "/b", "2", "def",
            "end",
            "length")
        assert psip.op_stack[-1] == 2

    def test_maxlength_dict(self):
        run("10", "dict", "maxlength")
        assert psip.op_stack[-1] == 10

    def test_def_requires_name(self):
        reset()
        psip.op_stack.extend([42, 99])
        with pytest.raises(psip.TypeMismatch):
            psip.def_operation()


# -------------------------------------------------------------------------------------
# STRINGS
# -------------------------------------------------------------------------------------
class TestStrings:
    def test_length_string(self):
        run("(hello)", "length")
        assert psip.op_stack[-1] == 5

    def test_get_string(self):
        run("(hello)", "0", "get")
        assert psip.op_stack[-1] == ord('h')

    def test_getinterval(self):
        run("(hello)", "1", "3", "getinterval")
        assert psip.op_stack[-1] == "ell"

    def test_putinterval(self):
        run("(hello)", "1", "(XY)", "putinterval")
        assert psip.op_stack[-1] == "hXYlo"


# -------------------------------------------------------------------------------------
# BOOLEAN / RELATIONAL
# -------------------------------------------------------------------------------------
class TestBoolean:
    def test_eq_true(self):
        assert run("5", "5", "eq")[-1] is True

    def test_eq_false(self):
        assert run("5", "6", "eq")[-1] is False

    def test_ne(self):
        assert run("5", "6", "ne")[-1] is True

    def test_ge(self):
        assert run("5", "5", "ge")[-1] is True
        assert run("5", "6", "ge")[-1] is False

    def test_gt(self):
        assert run("6", "5", "gt")[-1] is True

    def test_le(self):
        assert run("4", "5", "le")[-1] is True

    def test_lt(self):
        assert run("4", "5", "lt")[-1] is True

    def test_and_bool(self):
        assert run("true", "true", "and")[-1] is True
        assert run("true", "false", "and")[-1] is False

    def test_and_int(self):
        assert run("12", "10", "and")[-1] == (12 & 10)

    def test_or_bool(self):
        assert run("false", "true", "or")[-1] is True

    def test_or_int(self):
        assert run("12", "10", "or")[-1] == (12 | 10)

    def test_not_bool(self):
        assert run("true", "not")[-1] is False
        assert run("false", "not")[-1] is True

    def test_not_int(self):
        assert run("5", "not")[-1] == ~5

    def test_true_literal(self):
        assert run("true")[-1] is True

    def test_false_literal(self):
        assert run("false")[-1] is False

# -------------------------------------------------------------------------------------
# FLOW CONTROL
# -------------------------------------------------------------------------------------
class TestFlowControl:
    def test_if_true(self):
        run("true", "{ 42 }", "if")
        assert psip.op_stack[-1] == 42

    def test_if_false(self):
        reset()
        run("false", "{ 42 }", "if")
        assert 42 not in psip.op_stack

    def test_ifelse_true(self):
        run("true", "{ 1 }", "{ 2 }", "ifelse")
        assert psip.op_stack[-1] == 1

    def test_ifelse_false(self):
        run("false", "{ 1 }", "{ 2 }", "ifelse")
        assert psip.op_stack[-1] == 2

    def test_for(self):
        run("1", "1", "5", "{ }", "for")
        # 'for' pushes the loop variable each iteration; proc does nothing
        assert psip.op_stack == [1, 2, 3, 4, 5]

    def test_for_step(self):
        run("0", "2", "6", "{ }", "for")
        assert psip.op_stack == [0, 2, 4, 6]

    def test_for_negative_step(self):
        run("5", "-1", "1", "{ }", "for")
        assert psip.op_stack == [5, 4, 3, 2, 1]

    def test_repeat(self):
        run("3", "{ 7 }", "repeat")
        assert psip.op_stack == [7, 7, 7]

    def test_repeat_zero(self):
        run("0", "{ 99 }", "repeat")
        assert psip.op_stack == []


# -------------------------------------------------------------------------------------
# I/O (Output capture)
# -------------------------------------------------------------------------------------
class TestIO:
    def test_print(self, capsys):
        run("(hello)", "print")
        captured = capsys.readouterr()
        assert captured.out == "hello"

    def test_equals_int(self, capsys):
        run("42", "=")
        captured = capsys.readouterr()
        assert captured.out.strip() == "42"

    def test_equals_string(self, capsys):
        run("(world)", "=")
        captured = capsys.readouterr()
        assert captured.out.strip() == "world"

    def test_double_equals_string(self, capsys):
        run("(hello)", "==")
        captured = capsys.readouterr()
        assert captured.out.strip() == "(hello)"

    def test_double_equals_int(self, capsys):
        run("99", "==")
        captured = capsys.readouterr()
        assert captured.out.strip() == "99"


# -------------------------------------------------------------------------------------
# SCOPING
# -------------------------------------------------------------------------------------
class TestDynamicScoping:
    """
    Dynamic scoping example:
        /x 10 def
        /getX { x } def
        5 dict begin
            /x 99 def
            getX   % returns 99 (finds x in current runtime dict)
        end
    """
    def test_dynamic_sees_runtime_x(self):
        reset()
        psip.STATIC_SCOPING = False
        for t in ["/x", "10", "def",
                  "/getX", "{ x }", "def",
                  "5", "dict", "begin",
                  "/x", "99", "def",
                  "getX",
                  "end"]:
            psip.process_input(t)
        assert psip.op_stack[-1] == 99


class TestStaticScoping:
    """
    Static scoping example:
        /x 10 def
        /getX { x } def   % getX closes over the dict where x==10
        5 dict begin
            /x 99 def
            getX   % returns 10 (follows lexical chain, not runtime)
        end
    """
    def test_static_sees_definition_time_x(self):
        reset()
        psip.STATIC_SCOPING = True

        # In static mode, dict_operation sets parent = current top of dict_stack.
        # We simulate the same sequence as the dynamic test.
        for t in ["/x", "10", "def",
                  "/getX", "{ x }", "def",
                  "5", "dict", "begin",
                  "/x", "99", "def",
                  "getX",
                  "end"]:
            psip.process_input(t)

        # Under static scoping the procedure body { x } was stored when
        # dict_stack had only the built-in dict (which has x=10 after def).
        # The inner begin dict's parent chain goes: inner -> builtin.
        # So lookup finds x=10.
        assert psip.op_stack[-1] == 10

        psip.STATIC_SCOPING = False   # Restore for other tests