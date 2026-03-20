import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from pydantic import BaseModel
from typing import Optional, List


class Item(BaseModel):
    id: int
    name: str
    price: float
    is_offer: Optional[bool] = None


items_db = [
    Item(id=1, name="Foo", price=45.5, is_offer=None),
    Item(id=2, name="Bar", price=30.0, is_offer=None),
    Item(id=3, name="Baz", price=25.0, is_offer=None),
]

def get_items() -> List[Item]:
    return items_db

def get_item(item_id: int) -> Optional[Item]:
    for item in items_db:
        if item.id == item_id:
            return item
    return None

def create_item(item: Item) -> Item:
    items_db.append(item)
    return item

def update_item(item_id: int, item_update: Item) -> Optional[Item]:
    for index, item in enumerate(items_db):
        if item.id == item_id:
            items_db[index] = item_update
            return item_update
    return None

def delete_item(item_id: int) -> Optional[Item]:
    for index, item in enumerate(items_db):
        if item.id == item_id:
            return items_db.pop(index)
    return None

async def homepage(request):
    return Response("Hello, world", media_type="text/plain")

def read_items(request):
    return JSONResponse(get_items())

def read_item(request, item_id: int):
    item = get_item(item_id)
    if item:
        return JSONResponse(item)
    raise HTTPException(status_code=404, detail="Item not found")

def create_item_endpoint(request):
    new_item_data = request.json()
    try:
        new_item = Item(**new_item_data)
        created = create_item(new_item)
        return JSONResponse(created, status_code=201)
    except:
        raise HTTPException(status_code=422, detail="Invalid data")

def update_item_endpoint(request, item_id: int):
    update_data = request.json()
    try:
        updated_item = Item(id=item_id, **update_data)
        result = update_item(item_id, updated_item)
        if result:
            return JSONResponse(result)
        raise HTTPException(status_code=404, detail="Item not found")
    except:
        raise HTTPException(status_code=422, detail="Invalid data")

def delete_item_endpoint(request, item_id: int):
    deleted = delete_item(item_id)
    if deleted:
        return JSONResponse(deleted)
    raise HTTPException(status_code=404, detail="Item not found")

routes = [
    Route("/", endpoint=homepage),
    Route("/items/", endpoint=read_items, methods=["GET"]),
    Route("/items/{item_id}", endpoint=read_item, methods=["GET"]),
    Route("/items/", endpoint=create_item_endpoint, methods=["POST"]),
    Route("/items/{item_id}", endpoint=update_item_endpoint, methods=["PUT"]),
    Route("/items/{item_id}", endpoint=delete_item_endpoint, methods=["DELETE"]),
]

app = Starlette(routes=routes)

client = TestClient(app)

def test_items_read_one_isolated():
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "name": "Foo", "price": 45.5, "is_offer": None
    }

def test_items_read_all_isolated():
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Foo",
            "price": 45.5,
            "is_offer": None,
        },
        {
            "id": 2,
            "name": "Bar",
            "price": 30.0,
            "is_offer": None,
        },
        {
            "id": 3,
            "name": "Baz",
            "price": 25.0,
            "is_offer": None,
        },
    ]

def test_items_create_isolated():
    response = client.post("/items/", json={"name": "Bar", "price": 30.0, "is_offer": None})
    assert response.status_code == 200
    assert response.json() == {
        "id": 4, "name": "Bar", "price": 30.0, "is_offer": None
    }

def test_items_update_isolated():
    response = client.put("/items/1", json={"name": "Foo Updated", "price": 46.0, "is_offer": None})
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "name": "Foo Updated", "price": 46.0, "is_offer": None
    }

def test_items_delete_isolated():
    response = client.delete("/items/1")
    assert response.status_code == 200
    assert response.json() == {
        "id": 1, "name": "Foo Updated", "price": 46.0, "is_offer": None
    }

def test_invalid_item_id_isolated():
    response = client.get("/items/invalid")
    assert response.status_code == 422

def test_missing_item_id_isolated():
    response = client.get("/items/")
    assert response.status_code == 200

def test_create_item_with_invalid_data_isolated():
    response = client.post("/items/", json={"name": "Invalid", "price": "not-a-number"})
    assert response.status_code == 422

