from itertools import chain
from sqlalchemy.ext.declarative.api import DeclarativeMeta
import sadisplay
from terms.core import terms, factset, network
from terms.core.terms import Base


def main():
    classes = [c for c in
            list(chain.from_iterable([[getattr(m, a) for a in dir(m)]
                for m in (terms, factset, network)]))
            if type(c) is DeclarativeMeta and issubclass(c, Base)]
    print(classes)

    desc = sadisplay.describe(classes, show_methods=False)
    open('schema.plantuml', 'w').write(sadisplay.plantuml(desc))
    open('schema.dot', 'w').write(sadisplay.dot(desc))
