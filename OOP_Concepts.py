"""
An object is any entity that has attributes and behaviors. For example, a parrot is an object. It has
attributes - name, age, color, etc.
behavior - dancing, singing, etc.
Similarly, a class is a blueprint for that object.
"""

class Parrot:

    # class 
    name = ""
    age = 0

#  parrot1 object
parrot1 = Parrot()
parrot1.name = "Blu"
parrot1.age = 10


parrot2 = Parrot()
parrot2.name = "Woo"
parrot2.age = 15


print(f"{parrot1.name} is {parrot1.age} years old")
print(f"{parrot2.name} is {parrot2.age} years old")



""" In the above example, a class was created with the name Parrot with two attributes: name and age.
Then, instances of the Parrot class was created. Here, parrot1 and parrot2 are values to  new objects."""





""" Inheritance is a way of creating a new class for using details of an existing class without modifying it.
The newly formed class is a derived class or known as child class. 
Similarly,the existing class is a base class or parent class."""


# base 
class Animal:
    
    def eat(self):
        print( "I can eat!")
    
    def sleep(self):
        print("I can sleep!")

# derived 
class Dog(Animal):
    
    def bark(self):
        print("I can bark! Woof woof!!")

# object of the Dog class
dog1 = Dog()

dog1.eat()
dog1.sleep()

dog1.bark();



""" Here, dog1 is the object of derived class Dog which  can access members of the base class Animal.
 It's because Dog is inherited from Animal. """




""" Encapsulation is one of the key features of object-oriented programming. Encapsulation refers to the bundling of attributes and methods
 inside a single class.
It prevents outer classes from accessing and changing attributes and methods of a class. 
This also helps to achieve data hiding.
"""

class Computer:

    def __init__(self):
        self.__maxprice = 900

    def sell(self):
        print("Selling Price: {}".format(self.__maxprice))

    def setMaxPrice(self, price):
        self.__maxprice = price

c = Computer()
c.sell()

# changing the price
c.__maxprice = 1000
c.sell()

#setter function
c.setMaxPrice(1000)
c.sell()


"""In the above program, i defined a Computer class.

I used __init__() method to store the maximum selling price of Computer. Here,

c.__maxprice = 1000
Here,I have tried to modify the value of __maxprice outside of the class. 
However, since __maxprice is a private variable, this modification is not seen on the output.
As shown, to change the value, we have to use a setter function i.e setMaxPrice() which takes price as a parameter."""



"""  Polymorphism is another important concept of object-oriented programming. It simply means more than one form.
That is, the same entity (method or operator or object) can perform different operations in different scenarios.
"""

class Polygon:
    def render(self):
        print("Rendering Polygon...")

class Square(Polygon):
    def render(self):
        print("Rendering Square...")

class Circle(Polygon):
    def render(self):
        print("Rendering Circle...")
    
# object of Square
s1 = Square()
s1.render()

# object of Circle
c1 = Circle()
c1.render()

""" In the above example, i have created a superclass: Polygon and two subclasses: Square and Circle. 
The main purpose of the render() method is to render the shape. 
However, the process of rendering a square is different from the process of rendering a circle.
Hence, the render() method behaves differently in different classes. Or, we can say render() is polymorphic."""




"""Python dunder methods are special methods with double underscores in their names, like __init__ and __str__
They let  objects work naturally with built-in Python behavior, such as printing, adding, comparing, and looping.
Dunder methods live inside a class and Python calls them automatically in specific situations. """

class Book:
    def __init__(self, title, pages):
        self.title = title
        self.pages = pages

    
    def __str__(self):
        return f"{self.title} ({self.pages} pages)"

    
    def __repr__(self):
        return f"Book('{self.title}', {self.pages})"

    
    def __eq__(self, other):
        return self.pages == other.pages

book1 = Book("Clean Code", 464)
book2 = Book("Python Basics", 464)

print(book1)              
print(repr(book1))        
print(book1 == book2)     


"""  When to Use Dunder Methods:
Dunder methods help most when ywe want  own classes to feel like built-in types. 
Here are a few common use cases.
1) When we want better string output for debugging
Printing an object should tell us something useful. Nobody wants to read memory addresses all day.
2) When we want custom objects to support operators.
If our class represents something that has “math” behavior, like money, points, or measurements, operator support makes your code clean and readable.
3) When we want your objects to work with built-in functions
Built-ins like len(), iter(), sum(), sorted(), or membership checks (in) rely on dunder methods.
Adding the right methods lets your object work naturally in loops and conditions, like a list or dictionary.
4) When we want to control object creation and cleanup
Some dunder methods affect how objects are created and destroyed """



"""A decorator in Python is any callable Python object that is used to modify a function or a class. 
It takes in a function, adds some functionality, and returns it.
Decorators are a very powerful and useful tool in Python since it allows programmers to
modify/control the behaviour of a function or class.
Decorators are usually called before the definition of a function we want to decorate. 
There are two different kinds of decorators in Python:

Function decorators
Class decorators """


#function decorator
def test_decorator(func):
    def function_wrapper(x):
        print("Before calling " + func.__name__)
        res = func(x)
        print(res)
        print("After calling " + func.__name__)
    return function_wrapper
@test_decorator
def sqr(n):
    return n ** 2
sqr(54)



#class decorator
def add_greeting(cls):
    cls.greet = lambda self: "Hello from decorator!"
    return cls


@add_greeting
class Person:
    pass


p = Person()
print(p.greet())



"""When using Multiple Decorators for a single function, the decorators will be applied in the order
 they’ve been called."""

def lowercase_decorator(function):
    def wrapper():
        func = function()
        make_lowercase = func.lower()
        return make_lowercase
    return wrapper


def split_string(function):
    def wrapper():
        func = function()
        split_result = func.split()
        return split_result
    return wrapper


@split_string
@lowercase_decorator
def test_func():
    return 'MOTHER OF DRAGONS'


print(test_func())



"""So,Decorators are flexible way to modify or extend behavior of functions or methods, without changing their actual code.
A decorator is essentially a function that takes another function as an argument and returns a new function with enhanced functionality.
Decorators are often used in scenarios such as logging, authentication and memoization, 
allowing us to add additional functionality to existing functions or methods in a clean, reusable way."""



"""Generator functions act just like regular functions with just one difference they use the Python yield keyword instead of return .
 A generator function is a function that returns an iterator.
 Generator objects are used either by calling the next method on the generator object or using the generator object in a “for in” loop."""


def test_sequence():
    num = 0
    while num < 10:
        yield num
        num += 1
for i in test_sequence():
       print(i, end=",")



"""A return statement terminates a function entirely but a yield statement pauses the function saving 
all its states and later continues from there on successive calls."""


#Reverse a string
def reverse_str(test_str):
    length = len(test_str)
    for i in range(length - 1, -1, -1):
        yield test_str[i]
for char in reverse_str("Trojan"):
    print(char,end =" ")


