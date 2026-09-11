import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";
import { getConfidenceThreshold, updateTracker } from "./detectionTracker";

const AUTO_ADD_GUIDE = "사과 50% · 마늘·대파·새우 60% · 나머지 65%";

const PRODUCT_EMOJI = {
  마늘: "🧄",
  사과: "🍎",
  대파: "🌿",
  고기: "🥩",
  양파: "🧅",
  햄: "🍖",
  당근: "🥕",
  계란: "🥚",
  새우: "🦐",
  식빵: "🍞",
};

const RECIPE_EMOJI = {
  해물파전: "🥞",
  사과파이: "🥧",
  계란찜: "🍳",
  제육볶음: "🍲",
  새우볶음밥: "🍤",
};

const formatPrice = (price) => `${price.toLocaleString("ko-KR")}원`;

// Roboflow 클래스명을 DB 상품명으로 연결합니다.
const MODEL_PRODUCT_NAMES = {
  apple: "사과",
  bread: "식빵",
  carrot: "당근",
  egg: "계란",
  galic: "마늘", // 모델에 등록된 실제 철자
  "large green onion": "대파",
  l_onion: "대파",
  onion: "양파",
  raw_pork: "고기",
  shrimp: "새우",
  sliced_ham: "햄",
  garlic: "마늘",
  ham: "햄",
  meat: "고기",
  "green onion": "대파",
  green_onion: "대파",
  scallion: "대파",
};

function App() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [serverConnected, setServerConnected] = useState(false);
  const [cameraState, setCameraState] = useState("idle");
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [cart, setCart] = useState([]);
  const [totalPrice, setTotalPrice] = useState(0);
  const [purchaseResult, setPurchaseResult] = useState(null);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [recipeLoading, setRecipeLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [detecting, setDetecting] = useState(false);
  const [detections, setDetections] = useState(null);
  const detectionBusy = useRef(false);
  const tracks = useRef(new Map());
  const cameraSession = useRef(0);
  const productsLoaded = useRef(false);

  const showToast = useCallback((message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 2400);
  }, []);

  const loadCart = useCallback(async () => {
    try {
      if (!productsLoaded.current) {
        const productData = await api.getProducts();
        setProducts(productData);
        setSelectedProduct((current) => current || productData[0]?.name || "");
        productsLoaded.current = true;
      }
      const data = await api.getCart();
      setCart(data.cart);
      setTotalPrice(data.total_price);
      setServerConnected(true);
    } catch {
      setServerConnected(false);
    }
  }, []);

  useEffect(() => {
    async function loadPage() {
      try {
        const [, productData, cartData] = await Promise.all([
          api.checkServer(),
          api.getProducts(),
          api.getCart(),
        ]);
        setProducts(productData);
        productsLoaded.current = true;
        setSelectedProduct(productData[0]?.name || "");
        setCart(cartData.cart);
        setTotalPrice(cartData.total_price);
        setServerConnected(true);
      } catch {
        setServerConnected(false);
      }
    }

    loadPage();
    const intervalId = window.setInterval(loadCart, 2500);
    return () => window.clearInterval(intervalId);
  }, [loadCart]);

  useEffect(() => () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => {
    if (cameraState !== "active" || purchaseResult) return;
    let cancelled = false;
    let timer;
    const session = cameraSession.current;
    const valid = () => !cancelled && session === cameraSession.current;
    const controller = new AbortController();
    async function scan() {
      if (!valid()) return;
      const video = videoRef.current;
      if (document.hidden || !video?.videoWidth || video.readyState < 2 || detectionBusy.current) {
        for (const track of tracks.current.values()) track.since = null;
        timer = window.setTimeout(scan, 500);
        return;
      }
      detectionBusy.current = true;
      setDetecting(true);
      let failed = false;
      try {
        const canvas = document.createElement("canvas");
        const scale = Math.min(1, 960 / video.videoWidth);
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const capturedAt = performance.now();
        const result = await api.detect(canvas.toDataURL("image/jpeg", 0.85), controller.signal);
        if (!valid() || document.hidden) return;
        const grouped = new Map();
        for (const item of result.predictions) {
          const name = MODEL_PRODUCT_NAMES[item.class_name.trim().toLowerCase()] || item.class_name;
          if (!grouped.has(name) || grouped.get(name).confidence < item.confidence) {
            grouped.set(name, { ...item, name });
          }
        }
        const rows = updateTracker(tracks.current, [...grouped.values()], capturedAt);
        setDetections(rows);
        for (const row of rows) {
          if (!valid() || !row.ready || !products.some((product) => product.name === row.name)) continue;
          // Lock before sending: a lost response must not trigger duplicate cart writes.
          tracks.current.get(row.name).added = true;
          const data = await api.addToCart(row.name);
          if (!valid()) return;
          setCart(data.cart);
          setTotalPrice(data.total_price);
          row.added = true;
          showToast(`${row.name} 자동 추가 완료`);
        }
        if (valid()) setDetections([...rows]);
      } catch (error) {
        if (valid()) {
          failed = true;
          showToast(error.message);
          stopCamera();
        }
      } finally {
        detectionBusy.current = false;
        if (valid()) {
          setDetecting(false);
          if (!failed) timer = window.setTimeout(scan, 500);
        }
      }
    }
    scan();
    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [cameraState, purchaseResult, products, showToast]);

  async function startCamera() {
    try {
      cameraSession.current += 1;
      tracks.current.clear();
      setDetections(null);
      setCameraState("starting");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      setCameraState("active");
    } catch {
      setCameraState("error");
      showToast("카메라 권한을 확인해주세요.");
    }
  }

  function stopCamera() {
    cameraSession.current += 1;
    setDetecting(false);
    setDetections(null);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCameraState("idle");
  }

  async function addProduct(productName) {
    if (!productName || loading) return;
    try {
      setLoading(true);
      const data = await api.addToCart(productName);
      setCart(data.cart);
      setTotalPrice(data.total_price);
      showToast(data.message);
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function removeProduct(productName) {
    try {
      const data = await api.removeFromCart(productName);
      setCart(data.cart);
      setTotalPrice(data.total_price);
    } catch (error) {
      showToast(error.message);
    }
  }

  async function handlePurchase() {
    stopCamera();
    try {
      setLoading(true);
      setPurchaseResult(await api.purchase());
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      showToast(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function startNewShopping() {
    try {
      await api.clearCart();
      setCart([]);
      setTotalPrice(0);
      setPurchaseResult(null);
      setSelectedRecipe(null);
      showToast("새 쇼핑을 시작합니다.");
    } catch (error) {
      showToast(error.message);
    }
  }

  async function openRecipe(recipeId) {
    try {
      setRecipeLoading(true);
      setSelectedRecipe(await api.getRecipe(recipeId));
    } catch (error) {
      showToast(error.message);
    } finally {
      setRecipeLoading(false);
    }
  }

  const totalQuantity = cart.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <div className="app-shell">
      <Header
        connected={serverConnected}
        showingResult={Boolean(purchaseResult)}
        onBack={() => setPurchaseResult(null)}
      />

      <main className="page-container">
        {purchaseResult ? (
          <RecommendationView
            result={purchaseResult}
            onBack={() => setPurchaseResult(null)}
            onNewShopping={startNewShopping}
            onSelectRecipe={openRecipe}
            recipeLoading={recipeLoading}
          />
        ) : (
          <div className="shopping-grid">
            <CameraPanel
              videoRef={videoRef}
              cameraState={cameraState}
              onStart={startCamera}
              onStop={stopCamera}
              products={products}
              selectedProduct={selectedProduct}
              setSelectedProduct={setSelectedProduct}
              onTestDetection={() => addProduct(selectedProduct)}
              loading={loading}
              detecting={detecting}
              detections={detections}
            />
            <CartPanel
              cart={cart}
              totalPrice={totalPrice}
              totalQuantity={totalQuantity}
              onAdd={addProduct}
              onRemove={removeProduct}
              onPurchase={handlePurchase}
              loading={loading}
            />
          </div>
        )}
      </main>

      {toast && <div className="toast" role="status">{toast}</div>}
      {selectedRecipe && (
        <RecipeModal recipe={selectedRecipe} onClose={() => setSelectedRecipe(null)} />
      )}
    </div>
  );
}

function Header({ connected, showingResult, onBack }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <div className="brand-mark">🛒</div>
          <div>
            <strong>AI 스마트 카트</strong>
            <span>Smart Shopping Assistant</span>
          </div>
        </div>
        <div className="header-actions">
          {showingResult && (
            <button className="quiet-button" onClick={onBack}>← 장바구니로</button>
          )}
          <span className={`server-badge ${connected ? "online" : "offline"}`}>
            <i /> {connected ? "서버 연결됨" : "서버 연결 실패"}
          </span>
        </div>
      </div>
    </header>
  );
}

function CameraPanel({
  videoRef,
  cameraState,
  onStart,
  onStop,
  products,
  selectedProduct,
  setSelectedProduct,
  onTestDetection,
  loading,
  detecting,
  detections,
}) {
  const cameraActive = cameraState === "active";

  return (
    <section className="panel camera-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">LIVE DETECTION</span>
          <h2>상품 인식</h2>
        </div>
        <span className="mode-badge">모델 인식</span>
      </div>

      <div className={`camera-stage ${cameraActive ? "is-active" : ""}`}>
        <video ref={videoRef} autoPlay muted playsInline />
        {!cameraActive && (
          <div className="camera-placeholder">
            <div className="camera-icon">▣</div>
            <strong>
              {cameraState === "starting" ? "카메라를 준비하고 있습니다" : "상품을 카메라에 보여주세요"}
            </strong>
            <p>상품별 기준 이상으로 1초간 인식되면 자동으로 담깁니다. {AUTO_ADD_GUIDE}</p>
            <button className="camera-button" onClick={onStart} disabled={cameraState === "starting"}>
              {cameraState === "starting" ? "연결 중..." : "카메라 시작"}
            </button>
          </div>
        )}
        {cameraActive && (
          <>
            <div className="scan-line" />
            <div className="live-chip"><i /> {detecting ? "상품 확인 중" : "자동 인식 중"}</div>
            <button className="stop-camera" onClick={onStop}>카메라 끄기</button>
          </>
        )}
        <span className="corner top-left" />
        <span className="corner top-right" />
        <span className="corner bottom-left" />
        <span className="corner bottom-right" />
      </div>

      <p>{AUTO_ADD_GUIDE} 이상으로 1초 이상 확인된 상품을 자동으로 담습니다. 같은 상품은 화면에서 사라진 것이 확인된 뒤 다시 보여주세요.</p>
      <p>카메라가 켜져 있는 동안 사진을 인식 서버로 주기적으로 전송합니다.</p>
      {detections !== null && (
        <div aria-live="polite">
          {detections.length === 0 && <p>탐지된 상품이 없습니다. 상품을 더 가까이 보여주세요.</p>}
          {detections.map((detection, index) => {
            const name = detection.name;
            const known = products.some((product) => product.name === name);
            return (
              <div className="test-controls" key={index}>
                <span>{name} · {(detection.confidence * 100).toFixed(0)}%</span>
                {known ? <span>{detection.added ? "담기 완료 · 상품을 화면에서 치워주세요" : detection.confidence < getConfidenceThreshold(detection) ? `${Math.round(getConfidenceThreshold(detection) * 100)}% 이상 인식 대기` : `확인 중 ${Math.min(detection.seconds, 1).toFixed(1)} / 1초`}</span> : <span>{products.length === 0 ? "서버 상품 목록을 불러오는 중입니다" : `상품명 연결 필요 (${detection.class_name})`}</span>}
              </div>
            );
          })}
        </div>
      )}

      <details className="developer-test">
        <summary>개발용 상품 추가</summary>
        <div className="test-controls">
          <select value={selectedProduct} onChange={(event) => setSelectedProduct(event.target.value)}>
            {products.map((product) => (
              <option key={product.id} value={product.name}>
                {product.name} · {formatPrice(product.price)}
              </option>
            ))}
          </select>
          <button onClick={onTestDetection} disabled={!selectedProduct || loading}>
            선택 상품 인식
          </button>
        </div>
        <p>현재는 모델 대신 선택한 상품명을 장바구니 API로 전달합니다.</p>
      </details>
    </section>
  );
}

function CartPanel({ cart, totalPrice, totalQuantity, onAdd, onRemove, onPurchase, loading }) {
  return (
    <section className="panel cart-panel">
      <div className="panel-heading cart-heading">
        <div>
          <span className="eyebrow">MY CART</span>
          <h2>현재 장바구니</h2>
        </div>
        <span className="count-badge">{totalQuantity}</span>
      </div>

      <div className="cart-list">
        {cart.length === 0 ? (
          <div className="empty-cart">
            <div className="empty-icon">🛒</div>
            <strong>장바구니가 비어 있어요</strong>
            <p>상품을 카메라에 보여주세요.<br />상품별 기준 이상으로 1초간 확인되면 자동으로 담겨요.</p>
          </div>
        ) : (
          cart.map((item) => (
            <article className="cart-item" key={item.name}>
              <div className="product-symbol">{PRODUCT_EMOJI[item.name] || "📦"}</div>
              <div className="item-info">
                <strong>{item.name}</strong>
                <span>{formatPrice(item.price)}</span>
              </div>
              <div className="quantity-control" aria-label={`${item.name} 수량`}>
                <button onClick={() => onRemove(item.name)} aria-label={`${item.name} 하나 빼기`}>−</button>
                <b>{item.quantity}</b>
                <button onClick={() => onAdd(item.name)} aria-label={`${item.name} 하나 추가`}>+</button>
              </div>
              <strong className="line-price">{formatPrice(item.price * item.quantity)}</strong>
            </article>
          ))
        )}
      </div>

      <div className="cart-summary">
        <div><span>전체 상품 수</span><strong>{totalQuantity}개</strong></div>
        <div className="total-row"><span>총 구매금액</span><strong>{formatPrice(totalPrice)}</strong></div>
        <button className="purchase-button" onClick={onPurchase} disabled={!cart.length || loading}>
          {loading ? "재료 분석 중..." : "구매 완료 · 요리 추천 보기"}
        </button>
      </div>
    </section>
  );
}

function RecommendationView({ result, onBack, onNewShopping, onSelectRecipe, recipeLoading }) {
  const { can_make: canMake, need_more_ingredients: needMore } = result.recommendations;
  const ingredients = result.purchased_items.map((item) => item.name).join(", ");

  return (
    <section className="recommendation-view">
      <div className="result-header">
        <div>
          <span className="eyebrow">RECIPE RECOMMENDATION</span>
          <h1>요리 추천 결과</h1>
          <p>구매한 {ingredients} 재료를 기준으로 추천했어요.</p>
        </div>
        <div className="result-actions">
          <button className="quiet-button" onClick={onBack}>장바구니로</button>
          <button className="new-shopping-button" onClick={onNewShopping}>새 쇼핑 시작</button>
        </div>
      </div>

      <RecipeSection
        title="지금 만들 수 있는 요리"
        icon="✓"
        recipes={canMake}
        type="ready"
        emptyText="현재 재료만으로 완성할 수 있는 요리가 아직 없어요."
        onSelectRecipe={onSelectRecipe}
        recipeLoading={recipeLoading}
      />
      <RecipeSection
        title="재료를 추가하면 만들 수 있는 요리"
        icon="+"
        recipes={needMore}
        type="more"
        emptyText="추가 재료가 필요한 요리가 없습니다."
        onSelectRecipe={onSelectRecipe}
        recipeLoading={recipeLoading}
      />
    </section>
  );
}

function RecipeSection({ title, icon, recipes, type, emptyText, onSelectRecipe, recipeLoading }) {
  return (
    <div className={`recipe-section ${type}`}>
      <h2><span>{icon}</span>{title}<small>{recipes.length}개</small></h2>
      {recipes.length === 0 ? (
        <div className="empty-recipes">{emptyText}</div>
      ) : (
        <div className="recipe-grid">
          {recipes.map((recipe) => (
            <RecipeCard
              key={recipe.recipe_name}
              recipe={recipe}
              type={type}
              onSelect={() => onSelectRecipe(recipe.recipe_id)}
              loading={recipeLoading}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RecipeCard({ recipe, type, onSelect, loading }) {
  const missingDetails = recipe.missing_ingredient_details || [];

  return (
    <article className={`recipe-card ${type}`}>
      <div className="recipe-title">
        <div className="recipe-name">
          <span>{RECIPE_EMOJI[recipe.recipe_name] || "🍽️"}</span>
          <div>
            <strong>{recipe.recipe_name}</strong>
            <small>재료 {recipe.owned_ingredients.length}/{recipe.required_ingredients.length}가지 보유</small>
          </div>
        </div>
        <b>{recipe.can_make ? "바로 가능" : `${recipe.missing_ingredients.length}종 부족`}</b>
      </div>
      <div className="match-label"><span>재료 일치율</span><strong>{recipe.match_rate}%</strong></div>
      <div className="progress"><i style={{ width: `${recipe.match_rate}%` }} /></div>
      <div className="ingredient-tags">
        {recipe.owned_ingredients.map((ingredient) => (
          <span className="owned" key={ingredient}>✓ {ingredient}</span>
        ))}
        {missingDetails.map((ingredient) => (
          <span className="missing" key={ingredient.name}>
            × {ingredient.name} {ingredient.missing_quantity_text} 부족
          </span>
        ))}
      </div>
      {!recipe.can_make && (
        <p className="missing-summary">
          추가 필요: <strong>
            {missingDetails.map((ingredient) => (
              `${ingredient.name} ${ingredient.missing_quantity_text}`
            )).join(", ")}
          </strong>
        </p>
      )}
      <button className="recipe-detail-button" onClick={onSelect} disabled={loading}>
        {loading ? "불러오는 중..." : "요리법 보기 →"}
      </button>
    </article>
  );
}

function RecipeModal({ recipe, onClose }) {
  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section
        className="recipe-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="recipe-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-header">
          <div className="modal-recipe-title">
            <span>{RECIPE_EMOJI[recipe.name] || "🍽️"}</span>
            <div>
              <small>RECIPE GUIDE</small>
              <h2 id="recipe-modal-title">{recipe.name}</h2>
            </div>
          </div>
          <button onClick={onClose} aria-label="요리법 닫기">×</button>
        </div>

        <div className="modal-content">
          <div className="recipe-detail-section">
            <h3>필요한 재료</h3>
            <div className="detail-ingredients">
              {recipe.ingredients.map((ingredient) => (
                <div key={ingredient.name}>
                  <span>{PRODUCT_EMOJI[ingredient.name] || "📦"}</span>
                  <strong>{ingredient.name}</strong>
                  <b>{ingredient.quantity_text}</b>
                </div>
              ))}
            </div>
          </div>

          <div className="recipe-detail-section">
            <h3>요리 방법</h3>
            <ol className="cooking-steps">
              {recipe.steps.map((step) => (
                <li key={step.step_number}>
                  <span>{step.step_number}</span>
                  <p>{step.instruction}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </section>
    </div>
  );
}

export default App;
