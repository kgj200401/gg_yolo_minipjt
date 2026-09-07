const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "요청을 처리하지 못했습니다.");
  }

  return response.json();
}

export const api = {
  checkServer: () => request("/"),
  getProducts: () => request("/products"),
  getCart: () => request("/cart"),
  addToCart: (productName) => request("/cart/add", {
    method: "POST",
    body: JSON.stringify({ product_name: productName }),
  }),
  removeFromCart: (productName) => request("/cart/remove", {
    method: "POST",
    body: JSON.stringify({ product_name: productName }),
  }),
  clearCart: () => request("/cart", { method: "DELETE" }),
  purchase: () => request("/purchase", { method: "POST" }),
  getRecipe: (recipeId) => request(`/recipes/${recipeId}`),
};
