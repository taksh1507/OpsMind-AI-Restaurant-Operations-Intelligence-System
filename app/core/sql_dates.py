"""Database-independent UTC calendar dates with a consistent Python date type."""

from sqlalchemy import Date
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class utc_date(FunctionElement):
    type = Date()
    inherit_cache = True


@compiles(utc_date)
def compile_date(element, compiler, **kwargs):
    return "date(%s)" % compiler.process(element.clauses, **kwargs)


@compiles(utc_date, "postgresql")
def compile_postgres_date(element, compiler, **kwargs):
    return "date(timezone('UTC', %s))" % compiler.process(element.clauses, **kwargs)
