from dataclasses import dataclass, field
from dataclasses import MISSING

@dataclass
class Sample:
    name: str = "hello"

        

@dataclass
class Sample2(Sample):
    cheese: str = field(default=None)


print(Sample2())


