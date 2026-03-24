# tpl_admin_panels.py

ADMIN_INVENTORY_TABS = """
<div class="nav-tabs">
    <a href="/admin/inventory/ingredients">🥬 Ингредиенты</a>
    <a href="/admin/inventory/tech_cards">📜 Техкарты</a>
    <a href="/admin/inventory/stock">📦 Остатки</a>
    <a href="/admin/inventory/docs">📄 Документы</a>
    <a href="/admin/inventory/reports/usage">📉 Рух (Звіт)</a>
    <a href="/admin/inventory/checks">📝 Інвентаризація</a> <a href="/admin/inventory/reports/usage">📉 Рух (Звіт)</a>
    <a href="/admin/inventory/reports/suppliers">🚛 Постачальники</a>
</div>
"""

ADMIN_TABLES_BODY = """
<style>
    .qr-code-img {{
        width: 100px;
        height: 100px;
        border: 1px solid var(--border-light);
        padding: 5px;
        background: white;
    }}
    /* Стиль для селекта з множинним вибором */
    #waiter_ids_select {{
        height: 250px;
        width: 100%;
    }}
</style>
<div class="card">
    <h2><i class="fa-solid fa-plus"></i> Додати новий столик</h2>
    <form action="/admin/tables/add" method="post" class="search-form">
        <input type="text" id="name" name="name" placeholder="Назва або номер столика" required>
        <button type="submit">Додати столик</button>
    </form>
</div>
<div class="card">
    <h2><i class="fa-solid fa-chair"></i> Список столиків</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Назва</th>
                    <th>QR-код</th>
                    <th>Закріплені офіціанти</th>
                    <th>Дії</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</div>
<div class="modal-overlay" id="assign-waiter-modal">
    <div class="modal">
        <div class="modal-header">
            <h4 id="modal-title">Призначити офіціантів для столика</h4>
            <button type="button" class="close-button" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <form id="assign-waiter-form" method="post">
                <label for="waiter_ids_select">Виберіть офіціантів (на зміні):</label>
                <p style="font-size: 0.8rem; margin-bottom: 10px;">(Утримуйте Ctrl/Cmd для вибору кількох)</p>
                <select id="waiter_ids_select" name="waiter_ids" multiple>
                    </select>
                <br><br>
                <button type="submit">Призначити</button>
            </form>
        </div>
    </div>
</div>
<script>
function openAssignWaiterModal(tableId, tableName, waiters, assignedWaiterIds) {{
    const modal = document.getElementById('assign-waiter-modal');
    const form = document.getElementById('assign-waiter-form');
    const select = document.getElementById('waiter_ids_select');
    const title = document.getElementById('modal-title');
    
    title.innerText = `Призначити офіціантів для столика "${{tableName}}"`;
    form.action = `/admin/tables/assign_waiter/${{tableId}}`;
    select.innerHTML = ''; // Очищуємо список
    
    waiters.forEach(waiter => {{
        const option = document.createElement('option');
        option.value = waiter.id;
        option.textContent = waiter.full_name;
        // Перевіряємо, чи цей офіціант вже призначений
        if (assignedWaiterIds.includes(waiter.id)) {{
            option.selected = true;
        }}
        select.appendChild(option);
    }});
    
    modal.classList.add('active');
}}

function closeModal() {{
    document.getElementById('assign-waiter-modal').classList.remove('active');
}}

// Закриття модального вікна по кліку поза ним
window.onclick = function(event) {{
    const modal = document.getElementById('assign-waiter-modal');
    if (event.target == modal) {{
        closeModal();
    }}
}}
</script>
"""

ADMIN_ORDER_FORM_BODY = """
<style>
    .form-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 1.5rem;
    }
    @media (min-width: 768px) {
        .form-grid { grid-template-columns: repeat(2, 1fr); }
    }
    .order-items-table .quantity-input {
        width: 70px;
        text-align: center;
        padding: 0.5rem;
    }
    .order-items-table .actions button {
        background: none; border: none; color: var(--status-red);
        cursor: pointer; font-size: 1.2rem;
    }
    .totals-summary {
        text-align: right;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .totals-summary div { margin-bottom: 0.5rem; }
    .totals-summary .total { font-size: 1.4rem; color: var(--primary-color); }
    
    #product-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
    }
    .product-list-item {
        border: 1px solid var(--border-light);
        border-radius: 0.5rem;
        padding: 1rem;
        cursor: pointer;
        transition: border-color 0.2s, box-shadow 0.2s;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .product-list-item:hover {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px #bfdbfe;
    }
    .product-list-item h5 { font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem;}
    .product-list-item p { font-size: 0.9rem; color: #6b7280; }
    body.dark-mode .product-list-item p { color: #9ca3af; }
</style>

<div class="card">
    <form id="order-form" method="POST">
        <h3>Інформація про клієнта</h3>
        <div class="form-grid">
            <div class="form-group">
                <label for="phone_number">Номер телефону</label>
                <input type="tel" id="phone_number" placeholder="+380 (XX) XXX-XX-XX" required>
            </div>
            <div class="form-group">
                <label for="customer_name">Ім'я клієнта</label>
                <input type="text" id="customer_name" required>
            </div>
        </div>
        <div class="form-group">
            <label>Тип замовлення</label>
            <select id="delivery_type">
                <option value="delivery">Доставка</option>
                <option value="pickup">Самовивіз</option>
            </select>
        </div>
        <div class="form-group" id="address-group">
            <label for="address">Адреса доставки</label>
            <textarea id="address" rows="2"></textarea>
        </div>

        <h3>Склад замовлення</h3>
        <div class="table-wrapper">
            <table class="order-items-table">
                <thead>
                    <tr>
                        <th>Страва</th>
                        <th>Ціна</th>
                        <th>Кількість</th>
                        <th>Сума</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="order-items-body">
                </tbody>
            </table>
        </div>
        <div style="margin-top: 1.5rem; display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 1rem;">
            <button type="button" class="button" id="add-product-btn">
                <i class="fa-solid fa-plus"></i> Додати страву
            </button>
            <div class="totals-summary">
                <div class="total">До сплати: <span id="grand-total">0.00</span> грн</div>
            </div>
        </div>

        <div style="border-top: 1px solid var(--border-light); margin-top: 2rem; padding-top: 1.5rem; display: flex; justify-content: flex-end; gap: 1rem;">
             <a href="/admin/orders" class="button secondary">Скасувати</a>
             <button type="submit" class="button">Зберегти замовлення</button>
        </div>
    </form>
</div>

<div class="modal-overlay" id="product-modal">
    <div class="modal">
        <div class="modal-header">
            <h4>Вибір страви</h4>
            <button type="button" class="close-button" id="close-modal-btn">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-group">
                <input type="text" id="product-search-input" placeholder="Пошук страви за назвою...">
            </div>
            <div id="product-list">
            </div>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // State
    let orderItems = {};
    let allProducts = [];

    // Element References
    const orderForm = document.getElementById('order-form');
    const orderItemsBody = document.getElementById('order-items-body');
    const grandTotalEl = document.getElementById('grand-total');
    const deliveryTypeSelect = document.getElementById('delivery_type');
    const addressGroup = document.getElementById('address-group');
    const addProductBtn = document.getElementById('add-product-btn');
    const productModal = document.getElementById('product-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const productListContainer = document.getElementById('product-list');
    const productSearchInput = document.getElementById('product-search-input');

    // API Function
    const fetchAllProducts = async () => {
        try {
            const response = await fetch('/api/admin/products');
            if (!response.ok) throw new Error('Failed to fetch products');
            return await response.json();
        } catch (error) {
            console.error("Fetch products error:", error);
            alert('Помилка мережі при завантаженні страв.');
            return [];
        }
    };

    // Core Logic
    const calculateTotals = () => {
        let currentTotal = 0;
        for (const id in orderItems) {
            currentTotal += orderItems[id].price * orderItems[id].quantity;
        }
        grandTotalEl.textContent = currentTotal.toFixed(2);
    };

    const renderOrderItems = () => {
        orderItemsBody.innerHTML = '';
        if (Object.keys(orderItems).length === 0) {
            orderItemsBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Додайте страви до замовлення</td></tr>';
        } else {
            for (const id in orderItems) {
                const item = orderItems[id];
                const row = document.createElement('tr');
                row.dataset.id = id;
                row.innerHTML = `
                    <td>${item.name}</td>
                    <td>${item.price.toFixed(2)} грн</td>
                    <td><input type="number" class="quantity-input" value="${item.quantity}" min="1" data-id="${id}"></td>
                    <td>${(item.price * item.quantity).toFixed(2)} грн</td>
                    <td class="actions"><button type="button" class="remove-item-btn" data-id="${id}">&times;</button></td>
                `;
                orderItemsBody.appendChild(row);
            }
        }
        calculateTotals();
    };

    const addProductToOrder = (product) => {
        if (orderItems[product.id]) {
            orderItems[product.id].quantity++;
        } else {
            orderItems[product.id] = { name: product.name, price: product.price, quantity: 1 };
        }
        renderOrderItems();
    };

    // Modal Logic
    const renderProductsInModal = (products) => {
        productListContainer.innerHTML = '';
        products.forEach(p => {
            const itemEl = document.createElement('div');
            itemEl.className = 'product-list-item';
            itemEl.dataset.id = p.id;
            itemEl.innerHTML = `
                <div><h5>${p.name}</h5><p>${p.category}</p></div>
                <p><strong>${p.price.toFixed(2)} грн</strong></p>`;
            productListContainer.appendChild(itemEl);
        });
    };

    const openProductModal = async () => {
        productListContainer.innerHTML = '<p>Завантаження страв...</p>';
        productModal.classList.add('active');
        if (allProducts.length === 0) {
             allProducts = await fetchAllProducts();
        }
        renderProductsInModal(allProducts);
    };

    const closeProductModal = () => {
        productModal.classList.remove('active');
        productSearchInput.value = '';
    };

    window.initializeForm = (data) => {
        if (!data) {
            console.error("Initial order data is not provided!");
            orderForm.action = '/api/admin/order/new';
            orderForm.querySelector('button[type="submit"]').textContent = 'Створити замовлення';
            orderItems = {};
            renderOrderItems();
            return;
        }

        orderForm.action = data.action;
        orderForm.querySelector('button[type="submit"]').textContent = data.submit_text;

        if (data.form_values) {
            document.getElementById('phone_number').value = data.form_values.phone_number || '';
            document.getElementById('customer_name').value = data.form_values.customer_name || '';
            document.getElementById('delivery_type').value = data.form_values.is_delivery ? "delivery" : "pickup";
            document.getElementById('address').value = data.form_values.address || '';
            deliveryTypeSelect.dispatchEvent(new Event('change'));
        }

        orderItems = data.items || {};
        renderOrderItems();
    };

    // Event Listeners
    deliveryTypeSelect.addEventListener('change', (e) => {
        addressGroup.style.display = e.target.value === 'delivery' ? 'block' : 'none';
    });

    addProductBtn.addEventListener('click', openProductModal);
    closeModalBtn.addEventListener('click', closeProductModal);
    productModal.addEventListener('click', (e) => { if (e.target === productModal) closeProductModal(); });

    productSearchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredProducts = allProducts.filter(p => p.name.toLowerCase().includes(searchTerm));
        renderProductsInModal(filteredProducts);
    });

    productListContainer.addEventListener('click', (e) => {
        const productEl = e.target.closest('.product-list-item');
        if (productEl) {
            const product = allProducts.find(p => p.id == productEl.dataset.id);
            if (product) addProductToOrder(product);
            closeProductModal();
        }
    });

    orderItemsBody.addEventListener('change', (e) => {
        if (e.target.classList.contains('quantity-input')) {
            const id = e.target.dataset.id;
            const newQuantity = parseInt(e.target.value, 10);
            if (newQuantity > 0) {
                if (orderItems[id]) orderItems[id].quantity = newQuantity;
            } else {
                 delete orderItems[id];
            }
            renderOrderItems();
        }
    });

    orderItemsBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-item-btn')) {
            delete orderItems[e.target.dataset.id];
            renderOrderItems();
        }
    });

    orderForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const saveButton = orderForm.querySelector('button[type="submit"]');
        const originalButtonText = saveButton.textContent;
        saveButton.textContent = 'Збереження...';
        saveButton.disabled = true;

        const payload = {
            customer_name: document.getElementById('customer_name').value,
            phone_number: document.getElementById('phone_number').value,
            delivery_type: document.getElementById('delivery_type').value,
            address: document.getElementById('address').value,
            items: orderItems
        };

        try {
            const response = await fetch(orderForm.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (response.ok) {
                alert(result.message);
                window.location.href = result.redirect_url || '/admin/orders';
            } else {
                alert(`Помилка: ${result.detail || 'Невідома помилка'}`);
                saveButton.textContent = originalButtonText;
                saveButton.disabled = false;
            }
        } catch (error) {
            console.error("Submit error:", error);
            alert('Помилка мережі. Не вдалося зберегти замовлення.');
            saveButton.textContent = originalButtonText;
            saveButton.disabled = false;
        }
    });

    if (typeof window.initializeForm === 'function' && !window.initializeForm.invoked) {
        const newOrderData = {
             items: {},
             action: '/api/admin/order/new',
             submit_text: 'Створити замовлення',
             form_values: null
        };
        window.initializeForm(newOrderData);
        window.initializeForm.invoked = true;
    }
});
</script>
"""

ADMIN_EMPLOYEE_BODY = """
<div class="card">
    <ul class="nav-tabs">
        <li class="nav-item"><a href="/admin/employees" class="active">Співробітники</a></li>
        <li class="nav-item"><a href="/admin/roles">Ролі</a></li>
    </ul>
    <h2>👤 Додати співробітника</h2>
    <form action="/admin/add_employee" method="post">
        <label for="full_name">Повне ім'я:</label><input type="text" id="full_name" name="full_name" required>
        <label for="phone_number">Номер телефону (для авторизації):</label><input type="text" id="phone_number" name="phone_number" placeholder="+380XX XXX XX XX" required>
        <label for="role_id">Роль:</label><select id="role_id" name="role_id" required>{role_options}</select>
        
        <label for="password">Пароль для входу (PWA):</label>
        <input type="text" id="password" name="password" placeholder="Введіть пароль">
        
        <button type="submit">Додати співробітника</button>
    </form>
</div>
<div class="card">
    <h2>👥 Список співробітників</h2>
    <p>🟢 - На зміні (авторизований)</p>
    <table><thead><tr><th>ID</th><th>Ім'я</th><th>Телефон</th><th>Роль</th><th>Статус</th><th>Telegram ID</th><th>Дії</th></tr></thead><tbody>
    {rows}
    </tbody></table>
</div>
"""

ADMIN_ROLES_BODY = """
<div class="card">
    <ul class="nav-tabs">
        <li class="nav-item"><a href="/admin/employees">Співробітники</a></li>
        <li class="nav-item"><a href="/admin/roles" class="active">Ролі</a></li>
    </ul>
    <h2>Додати нову роль</h2>
    <form action="/admin/add_role" method="post">
        <label for="name">Назва ролі:</label><input type="text" id="name" name="name" required>
        <div class="checkbox-group">
            <input type="checkbox" id="can_manage_orders" name="can_manage_orders" value="true">
            <label for="can_manage_orders">Може керувати замовленнями (Оператор)</label>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="can_be_assigned" name="can_be_assigned" value="true">
            <label for="can_be_assigned">Може бути призначений на замовлення (Кур'єр)</label>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="can_serve_tables" name="can_serve_tables" value="true">
            <label for="can_serve_tables">Може обслуговувати столики (Офіціант)</label>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="can_receive_kitchen_orders" name="can_receive_kitchen_orders" value="true">
            <label for="can_receive_kitchen_orders">Отримує замовлення для приготування (Повар)</label>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="can_receive_bar_orders" name="can_receive_bar_orders" value="true">
            <label for="can_receive_bar_orders">Отримує замовлення для бару (Бармен)</label> 
        </div>
        <button type="submit">Додати роль</button>
    </form>
</div>
<div class="card">
    <h2>Список ролей</h2>
    <table><thead><tr><th>ID</th><th>Назва</th><th>Керув. замовл.</th><th>Признач. доставку</th><th>Обслуг. столики</th><th>Кухня</th><th>Бар</th><th>Дії</th></tr></thead><tbody>
    {rows}
    </tbody></table>
</div>
"""

ADMIN_REPORTS_BODY = """
<div class="card">
    <h2>📊 Выбор отчета</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">
        <a href="/admin/reports/cash_flow" class="report-link-card" style="display:block; padding:20px; background: #e3f2fd; border-radius:8px; text-decoration:none; color:#333; border:1px solid #90caf9;">
            <i class="fa-solid fa-money-bill-trend-up" style="font-size: 2em; color: #1976d2; margin-bottom:10px;"></i>
            <h3 style="margin:0;">Движение средств</h3>
            <p style="color:#666; font-size:0.9em;">Выручка, расходы, наличные и безнал.</p>
        </a>
        
        <a href="/admin/reports/workers" class="report-link-card" style="display:block; padding:20px; background: #fff3e0; border-radius:8px; text-decoration:none; color:#333; border:1px solid #ffcc80;">
            <i class="fa-solid fa-users-gear" style="font-size: 2em; color: #f57c00; margin-bottom:10px;"></i>
            <h3 style="margin:0;">Эффективность персонала</h3>
            <p style="color:#666; font-size:0.9em;">KPI сотрудников, количество заказов, продажи.</p>
        </a>

        <a href="/admin/reports/analytics" class="report-link-card" style="display:block; padding:20px; background: #e8f5e9; border-radius:8px; text-decoration:none; color:#333; border:1px solid #a5d6a7;">
            <i class="fa-solid fa-chart-column" style="font-size: 2em; color: #388e3c; margin-bottom:10px;"></i>
            <h3 style="margin:0;">Аналитика продаж</h3>
            <p style="color:#666; font-size:0.9em;">Топ блюд, категории.</p>
        </a>
        
        <a href="/admin/reports/couriers" class="report-link-card" style="display:block; padding:20px; background: #f3e5f5; border-radius:8px; text-decoration:none; color:#333; border:1px solid #ce93d8;">
            <i class="fa-solid fa-truck-fast" style="font-size: 2em; color: #8e24aa; margin-bottom:10px;"></i>
            <h3 style="margin:0;">Отчет по курьерам</h3>
            <p style="color:#666; font-size:0.9em;">Старый отчет по доставкам.</p>
        </a>
    </div>
</div>
"""

ADMIN_SETTINGS_BODY = """
<div class="card">
    <form action="/admin/settings" method="post" enctype="multipart/form-data">
        <h2>⚙️ Основні налаштування</h2>
        
        <h3>Зовнішній вигляд</h3>
        <label>Логотип (завантажте новий, щоб замінити):</label>
        <input type="file" name="logo_file" accept="image/*">
        {current_logo_html}

        <h3 style="margin-top: 2rem;">Налаштування Favicon</h3>
        <p>Завантажте необхідні файли favicon. Після завантаження оновіть сторінку (Ctrl+F5), щоб побачити зміни.</p>
        <h4>Поточні іконки</h4>
        <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap; margin-bottom: 2rem; background: #f0f0f0; padding: 1rem; border-radius: 8px;">
            <div><img src="/static/favicons/favicon-16x16.png?v={cache_buster}" alt="16x16" style="border: 1px solid #ccc;"><br><small>16x16</small></div>
            <div><img src="/static/favicons/favicon-32x32.png?v={cache_buster}" alt="32x32" style="border: 1px solid #ccc;"><br><small>32x32</small></div>
            <div><img src="/static/favicons/apple-touch-icon.png?v={cache_buster}" alt="Apple Touch Icon" style="width: 60px; height: 60px; border: 1px solid #ccc;"><br><small>Apple Icon</small></div>
            <div><img src="/static/favicons/icon-192.png?v={cache_buster}" alt="PWA 192x192" style="width: 60px; height: 60px; border: 1px solid #ccc;"><br><small>192x192</small></div>
            <div><img src="/static/favicons/icon-512.png?v={cache_buster}" alt="PWA 512x512" style="width: 60px; height: 60px; border: 1px solid #ccc;"><br><small>512x512</small></div>
        </div>

        <h4>Завантажити нові іконки</h4>
        <div class="form-grid" style="grid-template-columns: 1fr;">
            <div class="form-group"><label for="apple_touch_icon">apple-touch-icon.png (180x180)</label><input type="file" id="apple_touch_icon" name="apple_touch_icon" accept="image/png"></div>
            <div class="form-group"><label for="favicon_32x32">favicon-32x32.png</label><input type="file" id="favicon_32x32" name="favicon_32x32" accept="image/png"></div>
            <div class="form-group"><label for="favicon_16x16">favicon-16x16.png</label><input type="file" id="favicon_16x16" name="favicon_16x16" accept="image/png"></div>
            <div class="form-group"><label for="favicon_ico">favicon.ico (всі розміри)</label><input type="file" id="favicon_ico" name="favicon_ico" accept="image/x-icon"></div>
            <div class="form-group"><label for="icon_192">icon-192.png (Обов'язково для PWA, 192x192)</label><input type="file" id="icon_192" name="icon_192" accept="image/png"></div>
            <div class="form-group"><label for="icon_512">icon-512.png (Обов'язково для PWA, 512x512)</label><input type="file" id="icon_512" name="icon_512" accept="image/png"></div>
            <div class="form-group"><label for="site_webmanifest">site.webmanifest</label><input type="file" id="site_webmanifest" name="site_webmanifest" accept="application/manifest+json"></div>
        </div>
        
        <div style="margin-top: 2rem;">
            <button type="submit">Зберегти всі налаштування</button>
        </div>
    </form>
</div>
"""

ADMIN_MENU_BODY = """
<div class="card">
    <h2>{form_title}</h2>
    <form action="{form_action}" method="post">
        <label for="title">Заголовок (текст на кнопці):</label>
        <input type="text" id="title" name="title" value="{item_title}" required>
        
        <label for="content">Зміст сторінки (можна використовувати HTML-теги):</label>
        <textarea id="content" name="content" rows="10" required>{item_content}</textarea>
        
        <label for="sort_order">Порядок сортування (менше = вище):</label>
        <input type="number" id="sort_order" name="sort_order" value="{item_sort_order}" required>
        
        <div class="checkbox-group">
            <input type="checkbox" id="show_on_website" name="show_on_website" value="true" {item_show_on_website_checked}>
            <label for="show_on_website">Показувати на сайті</label>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="show_in_telegram" name="show_in_telegram" value="true" {item_show_in_telegram_checked}>
            <label for="show_in_telegram">Показувати в Telegram-боті</label>
        </div>
        
        <button type="submit">{button_text}</button>
        <a href="/admin/menu" class="button secondary">Скасувати</a>
    </form>
</div>
<div class="card">
    <h2>📜 Список сторінок</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Заголовок</th>
                    <th>Сортування</th>
                    <th>На сайті</th>
                    <th>В Telegram</th>
                    <th>Дії</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</div>
"""

ADMIN_ORDER_MANAGE_BODY = """
<style>
    .manage-grid {{
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 2rem;
    }}
    .order-details-card .detail-item {{
        display: flex;
        justify-content: space-between;
        padding: 0.75rem 0;
        border-bottom: 1px solid var(--border-light);
    }}
    .order-details-card .detail-item:last-child {{
        border-bottom: none;
    }}
    .order-details-card .detail-item strong {{
        color: #6b7280;
    }}
    body.dark-mode .order-details-card .detail-item strong {{
        color: #9ca3af;
    }}
    .status-history {{
        list-style-type: none;
        padding-left: 1rem;
        border-left: 2px solid var(--border-light);
    }}
    .status-history li {{
        margin-bottom: 0.75rem;
        position: relative;
        font-size: 0.9rem;
    }}
    .status-history li::before {{
        content: '✓';
        position: absolute;
        left: -1.1rem;
        top: 2px;
        color: var(--primary-color);
        font-weight: 900;
    }}
    @media (max-width: 992px) {{
        .manage-grid {{
            grid-template-columns: 1fr;
        }}
    }}
</style>
<div class="manage-grid">
    <div class="left-column">
        <div class="card order-details-card">
            <h2>Деталі замовлення #{order_id}</h2>
            <div class="detail-item">
                <strong>Клієнт:</strong>
                <span>{customer_name}</span>
            </div>
            <div class="detail-item">
                <strong>Телефон:</strong>
                <span>{phone_number}</span>
            </div>
            <div class="detail-item">
                <strong>Адреса:</strong>
                <span>{address}</span>
            </div>
             <div class="detail-item">
                <strong>Сума:</strong>
                <span>{total_price} грн</span>
            </div>
            <div class="detail-item">
                <strong>Оплата:</strong>
                <span>{payment_method_text}</span>
            </div>
            <div class="detail-item" style="flex-direction: column; align-items: start;">
                <strong style="margin-bottom: 0.5rem;">Склад замовлення:</strong>
                <div>{products_html}</div>
            </div>
        </div>
        <div class="card">
            <h2>Історія статусів</h2>
            {history_html}
        </div>
    </div>
    <div class="right-column">
        <div class="card">
            <h2>Керування статусом</h2>
            <form action="/admin/order/manage/{order_id}/set_status" method="post">
                <label for="status_id">Новий статус:</label>
                <select name="status_id" id="status_id" required>
                    {status_options}
                </select>
                
                <label for="payment_method" style="margin-top:10px;">Метод оплати (для каси):</label>
                <select name="payment_method" id="payment_method">
                    <option value="cash" {sel_cash}>💵 Готівка</option>
                    <option value="card" {sel_card}>💳 Картка / Термінал</option>
                </select>

                <button type="submit" style="margin-top:15px;">Зберегти зміни</button>
            </form>
        </div>
        <div class="card">
            <h2>Призначення кур'єра</h2>
            <form action="/admin/order/manage/{order_id}/assign_courier" method="post">
                <label for="courier_id">Кур'єр (на зміні):</label>
                <select name="courier_id" id="courier_id" required>
                    {courier_options}
                </select>
                <button type="submit">Призначити кур'єра</button>
            </form>
        </div>
    </div>
</div>
"""

ADMIN_CLIENTS_LIST_BODY = """
<div class="card">
    <h2><i class="fa-solid fa-users-line"></i> Список клієнтів</h2>
    <form action="/admin/clients" method="get" class="search-form">
        <input type="text" name="search" placeholder="Пошук за іменем або телефоном..." value="{search_query}">
        <button type="submit">🔍 Знайти</button>
    </form>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Ім'я</th>
                    <th>Телефон</th>
                    <th>Всього замовлень</th>
                    <th>Загальна сума</th>
                    <th>Дії</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    {pagination}
</div>
"""

ADMIN_CLIENT_DETAIL_BODY = """
<style>
    .client-info-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }}
    .info-block {{
        background-color: var(--bg-light);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid var(--border-light);
    }}
    .info-block h4 {{
        font-size: 0.9rem;
        color: #6b7280;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }}
    .info-block p {{
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .order-summary-row {{
        cursor: pointer;
    }}
    .order-summary-row:hover {{
        background-color: #f3f4f6;
    }}
    body.dark-mode .order-summary-row:hover {{
        background-color: #374151;
    }}
    .order-details-row {{
        display: none;
    }}
    .details-content {{
        padding: 1.5rem;
        background-color: var(--bg-light);
    }}
    .status-history {{
        list-style-type: none;
        padding-left: 1rem;
        border-left: 2px solid var(--border-light);
    }}
    .status-history li {{
        margin-bottom: 0.5rem;
        position: relative;
    }}
    .status-history li::before {{
        content: '✓';
        position: absolute;
        left: -1.1rem;
        top: 2px;
        color: var(--primary-color);
        font-weight: 900;
    }}
</style>
<div class="card">
    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem;">
        <i class="fa-solid fa-user-circle" style="font-size: 3rem;"></i>
        <div>
            <h2 style="margin-bottom: 0;">{client_name}</h2>
            <a href="tel:{phone_number}">{phone_number}</a>
        </div>
    </div>
    <div class="client-info-grid">
        <div class="info-block">
            <h4>Остання адреса</h4>
            <p>{address}</p>
        </div>
        <div class="info-block">
            <h4>Всього замовлень</h4>
            <p>{total_orders}</p>
        </div>
        <div class="info-block">
            <h4>Загальна сума</h4>
            <p>{total_spent} грн</p>
        </div>
    </div>
</div>
<div class="card">
    <h3>Історія замовлень</h3>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Дата</th>
                    <th>Статус</th>
                    <th>Сума</th>
                    <th>Доставив</th>
                    <th>Деталі</th>
                </tr>
            </thead>
            <tbody>
                {order_rows}
            </tbody>
        </table>
    </div>
</div>
<script>
    function toggleDetails(row) {{
        const detailsRow = row.nextElementSibling;
        const icon = row.querySelector('i');
        if (detailsRow.style.display === 'table-row') {{
            detailsRow.style.display = 'none';
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }} else {{
            detailsRow.style.display = 'table-row';
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }}
    }}
</script>
"""

# !!! ЗМІНИ ВНЕСЕНІ В ЦЮ ЗМІННУ !!!
ADMIN_DESIGN_SETTINGS_BODY = """
<div class="card">
    <form action="/admin/design_settings" method="post" enctype="multipart/form-data">
        <h2><i class="fa-solid fa-file-signature"></i> Назви та SEO</h2>
        
        <label for="site_title">Назва сайту/закладу (SEO Title):</label>
        <input type="text" id="site_title" name="site_title" value="{site_title}" placeholder="Назва, що відображається на сайті та в адмін-панелі">
        
        <label for="site_header_text">Заголовок на сайті (під логотипом):</label>
        <input type="text" id="site_header_text" name="site_header_text" value="{site_header_text}" placeholder="Якщо пусто, буде як SEO заголовок">
        
        <label for="seo_description">SEO Опис (Description):</label>
        <textarea id="seo_description" name="seo_description" rows="3" placeholder="Короткий опис для пошукових систем (до 160 символів)">{seo_description}</textarea>
        
        <label for="seo_keywords">SEO Ключові слова (Keywords):</label>
        <input type="text" id="seo_keywords" name="seo_keywords" value="{seo_keywords}" placeholder="Наприклад: доставка їжі, ресторан, назва">

        <h2 style="margin-top: 2rem;"><i class="fa-solid fa-palette"></i> Дизайн та Кольори</h2>
        
        <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
            <div>
                <label for="primary_color">Основний колір (Акцент):</label>
                <input type="color" id="primary_color" name="primary_color" value="{primary_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="secondary_color">Додатковий колір:</label>
                <input type="color" id="secondary_color" name="secondary_color" value="{secondary_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="background_color">Колір фону сторінки:</label>
                <input type="color" id="background_color" name="background_color" value="{background_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="text_color">Колір основного тексту:</label>
                <input type="color" id="text_color" name="text_color" value="{text_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="footer_bg_color">Фон підвалу (Footer):</label>
                <input type="color" id="footer_bg_color" name="footer_bg_color" value="{footer_bg_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="footer_text_color">Текст підвалу:</label>
                <input type="color" id="footer_text_color" name="footer_text_color" value="{footer_text_color}" style="width: 100%; height: 40px;">
            </div>
        </div>
        
        <h3 style="margin-top: 1rem;">Навігація по категоріям</h3>
        <div class="form-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px;">
            <div>
                <label for="category_nav_bg_color">Колір фону (можна прозорий):</label>
                <input type="color" id="category_nav_bg_color" name="category_nav_bg_color" value="{category_nav_bg_color}" style="width: 100%; height: 40px;">
            </div>
            <div>
                <label for="category_nav_text_color">Колір тексту посилань:</label>
                <input type="color" id="category_nav_text_color" name="category_nav_text_color" value="{category_nav_text_color}" style="width: 100%; height: 40px;">
            </div>
        </div>
        
        <h3 style="margin-top: 2rem;">Зображення Шапки (Header)</h3>
        <label>Завантажте фонове зображення для шапки (Overlay буде додано автоматично):</label>
        <input type="file" name="header_image_file" accept="image/*">
        
        <div style="margin-top: 1rem;">
            <label for="font_family_sans">Основний шрифт (Без засічок):</label>
            <select id="font_family_sans" name="font_family_sans">
                {font_options_sans}
            </select>
            
            <label for="font_family_serif">Шрифт заголовків (Із засічками):</label>
            <select id="font_family_serif" name="font_family_serif">
                {font_options_serif}
            </select>
        </div>

        <h2 style="margin-top: 2rem; color: #e67e22;"><i class="fa-solid fa-truck-fast"></i> Умови доставки</h2>
        <div class="form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; background: #fff7ed; padding: 20px; border-radius: 12px; border: 1px solid #ffedd5;">
            <div>
                <label for="delivery_cost"><i class="fa-solid fa-money-bill"></i> Вартість доставки (грн):</label>
                <input type="number" step="0.01" id="delivery_cost" name="delivery_cost" value="{delivery_cost}" placeholder="0.00">
                <small style="color:#666;">Базова ціна доставки.</small>
            </div>
            <div>
                <label for="free_delivery_from"><i class="fa-solid fa-gift"></i> Безкоштовно від (грн):</label>
                <input type="number" step="0.01" id="free_delivery_from" name="free_delivery_from" value="{free_delivery_from}" placeholder="Залиште пустим, якщо немає">
                <small style="color:#666;">Сума замовлення, після якої доставка = 0 грн.</small>
            </div>
        </div>
        
        <div style="margin-top: 20px;">
            <label for="delivery_zones_content"><i class="fa-solid fa-map-location-dot"></i> Інформація про зони доставки (HTML):</label>
            <textarea id="delivery_zones_content" name="delivery_zones_content" rows="6" placeholder="<p>Центр: до 30 хв<br>Слобідка: до 60 хв</p>">{delivery_zones_content}</textarea>
            <small style="color:#666;">Цей текст відображатиметься у спливаючому вікні "Зони доставки" в кошику.</small>
        </div>

        <h2 style="margin-top: 2rem;"><i class="fa-solid fa-circle-info"></i> Підвал сайту (Контакти)</h2>
        <div class="form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <label for="footer_address"><i class="fa-solid fa-location-dot"></i> Адреса:</label>
                <input type="text" id="footer_address" name="footer_address" value="{footer_address}" placeholder="вул. Прикладна, 10">
            </div>
            <div>
                <label for="footer_phone"><i class="fa-solid fa-phone"></i> Телефон:</label>
                <input type="text" id="footer_phone" name="footer_phone" value="{footer_phone}" placeholder="+380 XX XXX XX XX">
            </div>
            <div>
                <label for="working_hours"><i class="fa-solid fa-clock"></i> Час роботи:</label>
                <input type="text" id="working_hours" name="working_hours" value="{working_hours}" placeholder="Пн-Нд: 10:00 - 22:00">
            </div>
        </div>
        
        <h4 style="margin-top: 1rem;">Налаштування Wi-Fi (для QR меню)</h4>
        <div class="form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <label for="wifi_ssid"><i class="fa-solid fa-wifi"></i> Назва мережі (SSID):</label>
                <input type="text" id="wifi_ssid" name="wifi_ssid" value="{wifi_ssid}" placeholder="Restaurant_WiFi">
            </div>
            <div>
                <label for="wifi_password"><i class="fa-solid fa-lock"></i> Пароль:</label>
                <input type="text" id="wifi_password" name="wifi_password" value="{wifi_password}" placeholder="securepass123">
            </div>
        </div>

        <div class="form-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 10px;">
            <div>
                <label for="instagram_url"><i class="fa-brands fa-instagram"></i> Instagram (посилання):</label>
                <input type="text" id="instagram_url" name="instagram_url" value="{instagram_url}" placeholder="https://instagram.com/...">
            </div>
            <div>
                <label for="facebook_url"><i class="fa-brands fa-facebook"></i> Facebook (посилання):</label>
                <input type="text" id="facebook_url" name="facebook_url" value="{facebook_url}" placeholder="https://facebook.com/...">
            </div>
        </div>
        
        <h2 style="margin-top: 2rem;"><i class="fa-brands fa-telegram"></i> Тексти Telegram-бота</h2>
        
        <label for="telegram_welcome_message">Привітальне повідомлення (Клієнт-бот):</label>
        <textarea id="telegram_welcome_message" name="telegram_welcome_message" rows="5" placeholder="Текст, який бачить користувач при старті бота.">{telegram_welcome_message}</textarea>
        <p style="font-size: 0.8rem; margin-top: -0.5rem; margin-bottom: 1rem;">Використовуйте <code>{{user_name}}</code>, щоб вставити ім'я користувача.</p>

        <div style="margin-top: 2rem;">
            <button type="submit">Зберегти налаштування</button>
        </div>
    </form>
</div>
"""

ADMIN_REPORT_CASH_FLOW_BODY = """
<div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
        <h2>💰 Отчет о движении денежных средств</h2>
        <a href="/admin/reports/cash_flow/export?date_from={date_from}&date_to={date_to}" class="button" style="background-color: #27ae60; text-decoration: none;">
            <i class="fa-solid fa-file-csv"></i> Экспорт в Excel (CSV)
        </a>
    </div>
    <form action="/admin/reports/cash_flow" method="get" class="search-form" style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin-top: 15px;">
        <label>Период:</label>
        <input type="date" name="date_from" value="{date_from}" required>
        <span>—</span>
        <input type="date" name="date_to" value="{date_to}" required>
        <button type="submit">Показать</button>
    </form>
</div>

<div class="card">
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
        <div style="background:#e8f5e9; padding:15px; border-radius:5px;">
            <small>Общая выручка</small>
            <div style="font-size:1.4em; font-weight:bold; color:#2e7d32;">{total_revenue} грн</div>
        </div>
        <div style="background:#fff3e0; padding:15px; border-radius:5px;">
            <small>Наличные</small>
            <div style="font-size:1.4em; font-weight:bold; color:#ef6c00;">{cash_revenue} грн</div>
        </div>
        <div style="background:#e3f2fd; padding:15px; border-radius:5px;">
            <small>Карта / Терминал</small>
            <div style="font-size:1.4em; font-weight:bold; color:#1565c0;">{card_revenue} грн</div>
        </div>
        <div style="background:#ffebee; padding:15px; border-radius:5px;">
            <small>Расходы (Изъятия)</small>
            <div style="font-size:1.4em; font-weight:bold; color:#c62828;">{total_expenses} грн</div>
        </div>
    </div>

    <h3 style="margin-top: 30px;"><i class="fa-solid fa-receipt"></i> Детализация доходов (Оплаченные заказы)</h3>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>ID Заказа</th>
                    <th>Время</th>
                    <th>Тип оплаты</th>
                    <th>Сумма</th>
                    <th style="text-align:center;">Детали</th>
                </tr>
            </thead>
            <tbody>
                {order_rows}
            </tbody>
        </table>
    </div>

    <h3 style="margin-top: 30px;"><i class="fa-solid fa-money-bill-transfer"></i> Служебные транзакции кассы</h3>
    <div class="table-wrapper">
        <table>
            <thead><tr><th>Дата</th><th>Тип</th><th>Сумма</th><th>Кассир</th><th>Комментарий</th></tr></thead>
            <tbody>{transaction_rows}</tbody>
        </table>
    </div>
</div>

<script>
function toggleOrderDetails(id) {{
    var el = document.getElementById(id);
    var icon = document.getElementById('icon-' + id);
    if (el.style.display === 'none') {{
        el.style.display = 'table-row';
        if(icon) icon.className = 'fa-solid fa-chevron-up';
    }} else {{
        el.style.display = 'none';
        if(icon) icon.className = 'fa-solid fa-chevron-down';
    }}
}}
</script>
"""

ADMIN_REPORT_WORKERS_BODY = """
<div class="card">
    <h2>👥 Отчет по сотрудникам</h2>
    <form action="/admin/reports/workers" method="get" class="search-form" style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
        <label>Период:</label>
        <input type="date" name="date_from" value="{date_from}" required>
        <span>—</span>
        <input type="date" name="date_to" value="{date_to}" required>
        <button type="submit">Показать</button>
    </form>
</div>

<div class="card">
    <table>
        <thead>
            <tr>
                <th>Сотрудник</th>
                <th>Роль</th>
                <th>Кол-во заказов</th>
                <th>Общая сумма продаж</th>
                <th>Средний чек</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""

ADMIN_REPORT_ANALYTICS_BODY = """
<div class="card">
    <h2>📈 Аналитика продаж (Топ блюд)</h2>
    <form action="/admin/reports/analytics" method="get" class="search-form" style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
        <label>Период:</label>
        <input type="date" name="date_from" value="{date_from}" required>
        <span>—</span>
        <input type="date" name="date_to" value="{date_to}" required>
        <button type="submit">Показать</button>
    </form>
</div>

<div class="card">
    <h3>Топ популярных позиций</h3>
    <table>
        <thead>
            <tr>
                <th>№</th>
                <th>Название блюда</th>
                <th>Продано (шт)</th>
                <th>Выручка (грн)</th>
                <th>Доля выручки</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""

ADMIN_MARKETING_BODY = """
<div class="card">
    <h2>📢 Маркетинговые всплывающие окна</h2>
    <p>Здесь вы можете создать баннер, который увидят клиенты при входе на сайт.</p>
    
    <form action="/admin/marketing/save" method="post" enctype="multipart/form-data">
        <input type="hidden" name="popup_id" value="{popup_id}">
        
        <label for="title">Заголовок:</label>
        <input type="text" id="title" name="title" value="{title}" placeholder="Например: Скидка -20% на пиццу!">
        
        <label for="content">Текст сообщения:</label>
        <textarea id="content" name="content" rows="4" placeholder="Текст акции...">{content}</textarea>
        
        <label>Изображение:</label>
        <input type="file" name="image_file" accept="image/*">
        {current_image_html}
        
        <div class="form-grid" style="grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div>
                <label for="button_text">Текст кнопки (необязательно):</label>
                <input type="text" id="button_text" name="button_text" value="{button_text}" placeholder="Подробнее">
            </div>
            <div>
                <label for="button_link">Ссылка кнопки:</label>
                <input type="text" id="button_link" name="button_link" value="{button_link}" placeholder="https://instagram.com/...">
            </div>
        </div>

        <div class="checkbox-group" style="margin-top: 15px;">
            <input type="checkbox" id="is_active" name="is_active" value="true" {is_active_checked}>
            <label for="is_active">✅ Включить показ всплывающего окна</label>
        </div>
        
        <div class="checkbox-group">
            <input type="checkbox" id="show_once" name="show_once" value="true" {show_once_checked}>
            <label for="show_once">👁 Показывать только 1 раз (запоминать клиента)</label>
        </div>
        
        <button type="submit" style="margin-top: 20px;">Сохранить настройки</button>
    </form>
</div>
"""