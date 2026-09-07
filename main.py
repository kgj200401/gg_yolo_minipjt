from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from models import CartItem, Product, Recipe, RecipeIngredient, RecipeStep
from detection import router as detection_router


# DB가 비어 있을 때 자동으로 등록할 기본 상품입니다.
INITIAL_PRODUCTS = [
    {"name": "마늘", "price": 3000},
    {"name": "사과", "price": 2500},
    {"name": "대파", "price": 2000},
    {"name": "고기", "price": 8000},
    {"name": "양파", "price": 2000},
    {"name": "햄", "price": 4000},
    {"name": "당근", "price": 1500},
    {"name": "계란", "price": 5000},
    {"name": "새우", "price": 7000},
    {"name": "식빵", "price": 3500},
]


# 기본 레시피, 대략적인 재료 수량, 요리 방법입니다.
INITIAL_RECIPES = [
    {
        "name": "해물파전",
        "ingredients": [
            {"name": "대파", "amount": 1, "unit": "대"},
            {"name": "새우", "amount": 8, "unit": "마리"},
            {"name": "계란", "amount": 1, "unit": "개"},
        ],
        "steps": [
            "대파는 길게 썰고 새우는 깨끗하게 손질합니다.",
            "그릇에 계란과 물을 넣어 섞은 뒤 대파와 새우를 넣습니다.",
            "달군 팬에 식용유를 두르고 반죽을 넓게 펼칩니다.",
            "앞뒤로 노릇하게 익힌 뒤 먹기 좋은 크기로 자릅니다.",
        ],
    },
    {
        "name": "사과파이",
        "ingredients": [
            {"name": "사과", "amount": 1, "unit": "개"},
            {"name": "식빵", "amount": 2, "unit": "장"},
            {"name": "계란", "amount": 1, "unit": "개"},
        ],
        "steps": [
            "사과를 작게 썰어 설탕과 함께 팬에서 부드럽게 볶습니다.",
            "식빵 가장자리를 자르고 밀대로 얇게 눌러줍니다.",
            "식빵 위에 볶은 사과를 올리고 반으로 접어 가장자리를 눌러줍니다.",
            "표면에 달걀물을 바르고 팬에서 앞뒤로 노릇하게 굽습니다.",
        ],
    },
    {
        "name": "계란찜",
        "ingredients": [
            {"name": "계란", "amount": 3, "unit": "개"},
            {"name": "대파", "amount": 0.5, "unit": "대"},
        ],
        "steps": [
            "계란을 그릇에 깨고 물과 소금을 조금 넣어 잘 풀어줍니다.",
            "대파를 잘게 썰어 계란물에 넣습니다.",
            "냄비에 계란물을 붓고 약한 불에서 천천히 저어줍니다.",
            "계란이 부드럽게 익으면 불을 끄고 뚜껑을 덮어 뜸을 들입니다.",
        ],
    },
    {
        "name": "제육볶음",
        "ingredients": [
            {"name": "고기", "amount": 1, "unit": "팩"},
            {"name": "양파", "amount": 0.5, "unit": "개"},
            {"name": "대파", "amount": 1, "unit": "대"},
            {"name": "마늘", "amount": 3, "unit": "쪽"},
        ],
        "steps": [
            "양파는 채 썰고 대파는 어슷하게 썰며 마늘은 다집니다.",
            "고기에 고추장, 간장, 설탕, 다진 마늘을 넣어 버무립니다.",
            "달군 팬에 양념한 고기를 넣고 중불에서 볶습니다.",
            "고기가 거의 익으면 양파와 대파를 넣고 함께 볶아 완성합니다.",
        ],
    },
    {
        "name": "새우볶음밥",
        "ingredients": [
            {"name": "새우", "amount": 8, "unit": "마리"},
            {"name": "계란", "amount": 1, "unit": "개"},
            {"name": "당근", "amount": 0.5, "unit": "개"},
            {"name": "대파", "amount": 0.5, "unit": "대"},
        ],
        "steps": [
            "새우는 손질하고 당근과 대파는 잘게 썰어줍니다.",
            "달군 팬에 식용유를 두르고 계란을 넣어 가볍게 볶습니다.",
            "새우, 당근, 대파를 넣고 새우가 익을 때까지 볶습니다.",
            "밥을 넣어 고루 섞고 소금이나 간장으로 간을 맞춥니다.",
        ],
    },
]


def update_existing_database_schema():
    """기존 DB를 삭제하지 않고 새 재료 수량 컬럼을 추가합니다."""
    column_names = {
        column["name"]
        for column in inspect(engine).get_columns("recipe_ingredients")
    }

    with engine.begin() as connection:
        if "amount" not in column_names:
            connection.execute(text(
                "ALTER TABLE recipe_ingredients "
                "ADD COLUMN amount FLOAT NOT NULL DEFAULT 1"
            ))
        if "unit" not in column_names:
            connection.execute(text(
                "ALTER TABLE recipe_ingredients "
                "ADD COLUMN unit VARCHAR NOT NULL DEFAULT '개'"
            ))


def seed_initial_data():
    """최초 실행 시 기본 상품과 레시피를 DB에 저장합니다."""
    db = SessionLocal()

    try:
        for product_data in INITIAL_PRODUCTS:
            product = db.query(Product).filter(
                Product.name == product_data["name"]
            ).first()
            if product is None:
                db.add(Product(**product_data))

        db.commit()

        products_by_name = {
            product.name: product
            for product in db.query(Product).all()
        }

        for recipe_data in INITIAL_RECIPES:
            recipe = db.query(Recipe).filter(
                Recipe.name == recipe_data["name"]
            ).first()

            if recipe is None:
                recipe = Recipe(name=recipe_data["name"])
                db.add(recipe)
                db.flush()

            for order, ingredient_data in enumerate(
                recipe_data["ingredients"],
                start=1,
            ):
                product = products_by_name[ingredient_data["name"]]
                recipe_ingredient = db.query(RecipeIngredient).filter(
                    RecipeIngredient.recipe_id == recipe.id,
                    RecipeIngredient.product_id == product.id,
                ).first()

                if recipe_ingredient is None:
                    recipe_ingredient = RecipeIngredient(
                        recipe_id=recipe.id,
                        product_id=product.id,
                    )
                    db.add(recipe_ingredient)

                recipe_ingredient.ingredient_order = order
                recipe_ingredient.amount = ingredient_data["amount"]
                recipe_ingredient.unit = ingredient_data["unit"]

            for step_number, instruction in enumerate(
                recipe_data["steps"],
                start=1,
            ):
                recipe_step = db.query(RecipeStep).filter(
                    RecipeStep.recipe_id == recipe.id,
                    RecipeStep.step_number == step_number,
                ).first()

                if recipe_step is None:
                    recipe_step = RecipeStep(
                        recipe_id=recipe.id,
                        step_number=step_number,
                    )
                    db.add(recipe_step)

                recipe_step.instruction = instruction

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시 테이블을 만들고 기본 데이터를 준비합니다.
    Base.metadata.create_all(bind=engine)
    update_existing_database_schema()
    seed_initial_data()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(detection_router)

# React 개발 서버에서 FastAPI를 호출할 수 있도록 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CartAddRequest(BaseModel):
    product_name: str


def get_cart_data(db: Session):
    """DB 장바구니를 기존 API 응답 형태로 변환합니다."""
    cart_items = db.query(CartItem).order_by(CartItem.id).all()
    cart = [
        {
            "name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
        }
        for item in cart_items
    ]
    total_price = sum(
        item["price"] * item["quantity"]
        for item in cart
    )

    return cart, total_price


def recommend_recipes(db: Session, cart):
    """장바구니 수량과 레시피의 필요 수량을 비교합니다."""
    cart_quantities = {
        item["name"]: item["quantity"]
        for item in cart
    }
    recommendations = []

    for recipe in db.query(Recipe).order_by(Recipe.id).all():
        required_ingredients = [
            ingredient.product.name
            for ingredient in recipe.ingredients
        ]
        owned_ingredients = [
            ingredient.product.name
            for ingredient in recipe.ingredients
            if cart_quantities.get(ingredient.product.name, 0)
            >= ingredient.amount
        ]
        missing_ingredient_details = []

        for ingredient in recipe.ingredients:
            ingredient_name = ingredient.product.name
            owned_quantity = cart_quantities.get(ingredient_name, 0)
            missing_amount = max(ingredient.amount - owned_quantity, 0)

            if missing_amount > 0:
                missing_ingredient_details.append({
                    "name": ingredient_name,
                    "required_amount": ingredient.amount,
                    "required_unit": ingredient.unit,
                    "owned_quantity": owned_quantity,
                    "missing_amount": missing_amount,
                    "missing_quantity_text": format_ingredient_amount(
                        missing_amount,
                        ingredient.unit,
                    ),
                })

        missing_ingredients = [
            ingredient["name"]
            for ingredient in missing_ingredient_details
        ]
        match_rate = round(
            len(owned_ingredients) / len(required_ingredients) * 100,
            1,
        )

        recommendations.append({
            "recipe_id": recipe.id,
            "recipe_name": recipe.name,
            "required_ingredients": required_ingredients,
            "owned_ingredients": owned_ingredients,
            "missing_ingredients": missing_ingredients,
            "missing_ingredient_details": missing_ingredient_details,
            "match_rate": match_rate,
            "can_make": len(missing_ingredients) == 0,
        })

    # 부족한 재료가 적고, 재료 일치율이 높은 요리를 먼저 보여줍니다.
    recommendations.sort(
        key=lambda recipe: (
            len(recipe["missing_ingredients"]),
            -recipe["match_rate"],
        )
    )

    return recommendations


def format_ingredient_amount(amount, unit):
    """0.5는 '반 개', 정수는 '1개'처럼 읽기 좋게 표시합니다."""
    if amount == 0.5:
        return f"반 {unit}"
    if amount == int(amount):
        return f"{int(amount)}{unit}"
    return f"{amount:g}{unit}"


@app.get("/")
def read_root():
    return {"message": "Smart Cart API is running"}


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).order_by(Product.id).all()
    return [
        {"id": product.id, "name": product.name, "price": product.price}
        for product in products
    ]


@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if recipe is None:
        raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")

    return {
        "id": recipe.id,
        "name": recipe.name,
        "ingredients": [
            {
                "name": ingredient.product.name,
                "amount": ingredient.amount,
                "unit": ingredient.unit,
                "quantity_text": format_ingredient_amount(
                    ingredient.amount,
                    ingredient.unit,
                ),
            }
            for ingredient in recipe.ingredients
        ],
        "steps": [
            {
                "step_number": step.step_number,
                "instruction": step.instruction,
            }
            for step in recipe.steps
        ],
    }


@app.post("/cart/add")
def add_to_cart(item: CartAddRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.name == item.product_name
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    cart_item = db.query(CartItem).filter(
        CartItem.product_id == product.id
    ).first()

    if cart_item:
        cart_item.quantity += 1
    else:
        db.add(CartItem(product_id=product.id, quantity=1))

    db.commit()
    cart, total_price = get_cart_data(db)

    return {
        "message": f"{product.name}이(가) 장바구니에 추가되었습니다.",
        "cart": cart,
        "total_price": total_price,
    }


@app.get("/cart")
def get_cart(db: Session = Depends(get_db)):
    cart, total_price = get_cart_data(db)
    return {
        "cart": cart,
        "total_price": total_price,
    }


@app.post("/cart/remove")
def remove_from_cart(item: CartAddRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.name == item.product_name
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    cart_item = db.query(CartItem).filter(
        CartItem.product_id == product.id
    ).first()

    if cart_item is None:
        raise HTTPException(
            status_code=404,
            detail="장바구니에 해당 상품이 없습니다.",
        )

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
    else:
        db.delete(cart_item)

    db.commit()
    cart, total_price = get_cart_data(db)
    return {"cart": cart, "total_price": total_price}


@app.delete("/cart")
def clear_cart(db: Session = Depends(get_db)):
    db.query(CartItem).delete()
    db.commit()
    return {"message": "장바구니를 비웠습니다.", "cart": [], "total_price": 0}


@app.post("/purchase")
def purchase(db: Session = Depends(get_db)):
    cart, total_price = get_cart_data(db)

    if not cart:
        raise HTTPException(
            status_code=400,
            detail="장바구니가 비어 있습니다. 상품을 먼저 추가해주세요.",
        )

    recommendations = recommend_recipes(db, cart)
    can_make = [
        recipe for recipe in recommendations
        if recipe["can_make"]
    ]
    need_more_ingredients = [
        recipe for recipe in recommendations
        if not recipe["can_make"]
    ]

    return {
        "message": "구매가 완료되었습니다. 장바구니 재료로 요리를 추천합니다.",
        "purchased_items": cart,
        "total_price": total_price,
        "recommendations": {
            "can_make": can_make,
            "need_more_ingredients": need_more_ingredients,
        },
    }
