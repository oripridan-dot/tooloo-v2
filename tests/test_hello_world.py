import pytest
from src.hello_world import hello_world

def test_hello_world_returns_greeting():
    assert hello_world() == "Hello, World!"
