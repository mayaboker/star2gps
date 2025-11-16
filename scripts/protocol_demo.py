from typing import Protocol

class Speaker(Protocol):
    def speak(self) -> None:
        ...

    def foo(self) -> None:
        print("This is a default method in the Protocol.")

class Dog(Speaker):
    def speak(self):
        self.foo()
        print("Woof!")

class Cat(Speaker):
    def speak(self):
        self.foo()
        print("Meow!")

def make_it_talk(animal: Speaker) -> None:
    animal.speak()

make_it_talk(Dog())
make_it_talk(Cat())