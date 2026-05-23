# Python Basics

Python is a high-level, interpreted programming language known for its readability and simplicity.

## Variables and Data Types

Python is dynamically typed, so you don't declare variable types explicitly.

```python
name = "Alice"       # str
age = 30             # int
height = 5.9         # float
is_active = True     # bool
```

Common built-in types include: `str`, `int`, `float`, `bool`, `list`, `dict`, `tuple`, `set`.

## Control Flow

### If/Elif/Else

```python
score = 85
if score >= 90:
    grade = "A"
elif score >= 75:
    grade = "B"
else:
    grade = "C"
```

### Loops

```python
# For loop over a list
for item in ["apple", "banana", "cherry"]:
    print(item)

# While loop
count = 0
while count < 5:
    count += 1
```

## Functions

Define functions with `def`. Arguments can have default values.

```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

print(greet("Bob"))           # Hello, Bob!
print(greet("Bob", "Hi"))     # Hi, Bob!
```

## Lists and Comprehensions

```python
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers if x % 2 == 0]
# squares = [4, 16]
```

## Dictionaries

```python
person = {"name": "Alice", "age": 30, "city": "London"}
print(person["name"])           # Alice
person["email"] = "a@b.com"    # add new key
```

## Error Handling

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"Error: {e}")
finally:
    print("Always runs")
```
