# staff_templates.py

# --- СТОРІНКА ВХОДУ ---
STAFF_LOGIN_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Вхід для персоналу</title>
    
    <link rel="manifest" href="/staff/manifest.json">
    <meta name="theme-color" content="#4f46e5">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
        :root {
            --primary: #4f46e5;
            --primary-dark: #4338ca;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --white: #ffffff;
            --gray-100: #f3f4f6;
            --text-dark: #1f2937;
            --text-light: #6b7280;
            --error-bg: #fee2e2;
            --error-text: #991b1b;
        }

        * { box-sizing: border-box; outline: none; }

        body { 
            font-family: 'Inter', sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            margin: 0; 
            background: var(--bg-gradient);
            background-size: 200% 200%;
            animation: gradientBG 15s ease infinite;
            padding: 20px;
        }

        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        .login-card { 
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 2.5rem; 
            border-radius: 24px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.2); 
            width: 100%; 
            max-width: 380px; 
            text-align: center; 
            border: 1px solid rgba(255,255,255,0.5);
            animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes fadeUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .brand-icon {
            width: 70px;
            height: 70px;
            background: var(--primary);
            color: white;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto 1.5rem;
            box-shadow: 0 10px 20px rgba(79, 70, 229, 0.3);
            transform: rotate(-5deg);
            transition: transform 0.3s ease;
        }
        
        .brand-icon:hover { transform: rotate(0deg) scale(1.05); }

        h2 { 
            margin: 0 0 0.5rem 0; 
            color: var(--text-dark); 
            font-weight: 800; 
            font-size: 1.8rem;
            letter-spacing: -0.02em;
        }
        
        p.subtitle {
            color: var(--text-light);
            margin: 0 0 2rem 0;
            font-size: 0.95rem;
        }

        .input-group {
            position: relative;
            margin-bottom: 1.2rem;
            text-align: left;
        }

        .input-group i {
            position: absolute;
            left: 16px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-light);
            font-size: 1.1rem;
            transition: color 0.2s;
            pointer-events: none;
        }

        input { 
            width: 100%; 
            padding: 16px 16px 16px 48px; 
            border: 2px solid transparent; 
            border-radius: 16px; 
            font-size: 1rem; 
            background: var(--gray-100); 
            color: var(--text-dark);
            transition: all 0.2s ease;
            font-family: inherit;
            font-weight: 500;
        }

        input:focus { 
            border-color: var(--primary); 
            background: var(--white); 
            box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1); 
        }

        input:focus + i { color: var(--primary); }

        button { 
            width: 100%; 
            padding: 16px; 
            background: var(--primary); 
            color: white; 
            border: none; 
            border-radius: 16px; 
            font-size: 1.05rem; 
            font-weight: 700; 
            cursor: pointer; 
            margin-top: 10px; 
            transition: all 0.2s; 
            box-shadow: 0 10px 20px rgba(79, 70, 229, 0.25);
            display: flex; align-items: center; justify-content: center; gap: 10px;
        }

        button:hover { 
            background: var(--primary-dark); 
            transform: translateY(-2px);
            box-shadow: 0 15px 30px rgba(79, 70, 229, 0.35);
        }
        
        button:active { transform: translateY(0); }

        .error-msg {
            background: var(--error-bg); 
            color: var(--error-text); 
            padding: 12px; 
            border-radius: 12px; 
            margin-bottom: 20px; 
            font-size: 0.9rem;
            display: none; 
            border: 1px solid rgba(220, 38, 38, 0.1);
            font-weight: 500;
            animation: shake 0.4s ease-in-out;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
        
        .footer {
            margin-top: 2rem;
            font-size: 0.8rem;
            color: var(--text-light);
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-icon">
            <i class="fa-solid fa-user-shield"></i>
        </div>
        <h2>Staff Panel</h2>
        <p class="subtitle">Система керування рестораном</p>
        
        <div id="error-box" class="error-msg">
            <i class="fa-solid fa-circle-exclamation"></i> Невірний телефон або пароль
        </div>
        
        <form action="/staff/login" method="post">
            <div class="input-group">
                <input type="tel" name="phone" placeholder="Номер телефону" required autocomplete="username">
                <i class="fa-solid fa-phone"></i>
            </div>
            
            <div class="input-group">
                <input type="password" name="password" placeholder="Пароль" required autocomplete="current-password">
                <i class="fa-solid fa-lock"></i>
            </div>
            
            <button type="submit">Увійти <i class="fa-solid fa-arrow-right"></i></button>
        </form>
        
        <div class="footer">
            &copy; 2024 Staff System
        </div>
    </div>

    <script>
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.has('error')) {
          document.getElementById('error-box').style.display = 'block';
      }

      if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
          navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW error:', err));
        });
      }
    </script>
</body>
</html>
"""

# --- ГОЛОВНА ПАНЕЛЬ (DASHBOARD) ---
STAFF_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{site_title} - Персонал</title>
    
    <link rel="manifest" href="/staff/manifest.json">
    <meta name="theme-color" content="#333333">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="/static/favicons/apple-touch-icon.png">
    <link rel="icon" type="image/png" href="/static/favicons/favicon-32x32.png">
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        :root {{ --primary: #333; --bg: #f4f4f4; --white: #fff; --green: #27ae60; --red: #e74c3c; --blue: #3498db; --orange: #f39c12; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: var(--bg); padding-bottom: 80px; -webkit-tap-highlight-color: transparent; user-select: none; }}
        
        /* HEADER */
        .dashboard-header {{ background: var(--white); padding: 15px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); position: sticky; top: 0; z-index: 100; }}
        .user-info h3 {{ margin: 0; font-size: 1.1rem; color: var(--primary); }}
        .role-badge {{ font-size: 0.75rem; background: #eee; padding: 3px 8px; border-radius: 6px; color: #555; display: inline-block; margin-top: 4px; }}
        .shift-btn {{ border: none; padding: 8px 16px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .shift-btn.on {{ background: #e8f5e9; color: var(--green); border: 1px solid var(--green); }}
        .shift-btn.off {{ background: #ffebee; color: var(--red); border: 1px solid var(--red); }}

        /* CONTENT */
        #main-view {{ padding: 15px; max-width: 800px; margin: 0 auto; min-height: 70vh; }}
        .empty-state {{ text-align: center; color: #999; margin-top: 50px; font-size: 0.9rem; display: flex; flex-direction: column; align-items: center; gap: 10px; }}
        .empty-state i {{ font-size: 2rem; opacity: 0.3; }}
        
        /* CARDS */
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }}
        .card {{ background: var(--white); border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.03); cursor: pointer; transition: transform 0.1s; border: 1px solid transparent; }}
        .card:active {{ transform: scale(0.96); background: #f9f9f9; }}
        
        .table-card {{ text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100px; }}
        .table-card .card-title {{ font-weight: 700; margin-bottom: 8px; font-size: 1.1rem; }}
        
        /* GROUP HEADERS */
        .table-group-header {{
            background: #eee; padding: 8px 15px; border-radius: 8px; font-weight: bold; color: #555;
            margin: 15px 0 10px; position: sticky; top: 70px; z-index: 90;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); display: flex; align-items: center; gap: 10px;
        }}
        
        /* FINANCE */
        .finance-card {{ background: var(--white); border-radius: 15px; padding: 25px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }}
        .finance-header {{ font-size: 0.9rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }}
        .finance-amount {{ font-size: 2.5rem; font-weight: 800; }}
        .finance-amount.red-text {{ color: var(--red); }}
        .finance-amount.green-text {{ color: var(--green); }}
        .debt-list {{ background: var(--white); border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }}
        .debt-item {{ display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #eee; }}
        .debt-item:last-child {{ border-bottom: none; }}
        
        /* ORDER CARDS */
        .order-card {{ margin-bottom: 15px; border-left: 5px solid var(--primary); position: relative; background: var(--white); padding: 15px; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .order-card .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; font-size: 0.9rem; color: #666; }}
        .order-card .order-id {{ font-size: 1.1rem; font-weight: 800; color: #333; }}
        .order-card .card-body {{ font-size: 0.95rem; line-height: 1.5; padding-bottom: 12px; border-bottom: 1px solid #eee; margin-bottom: 12px; }}
        .order-card .card-footer {{ display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap; }}
        .info-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }}
        .info-row i {{ width: 20px; text-align: center; color: #777; }}
        
        /* BADGES & BUTTONS */
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge.success {{ background: #e8f5e9; color: var(--green); }}
        .badge.alert {{ background: #ffebee; color: var(--red); }}
        .badge.warning {{ background: #fff3e0; color: var(--orange); }}
        .badge.info {{ background: #e3f2fd; color: var(--blue); }}

        .action-btn {{ background: var(--primary); color: var(--white); border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 0.9rem; display: inline-flex; align-items: center; gap: 6px; }}
        .action-btn.secondary {{ background: #f0f0f0; color: #333; }}
        .action-btn.danger {{ background: #fee2e2; color: #c0392b; }}
        .action-btn:active {{ opacity: 0.8; transform: translateY(1px); }}
        
        /* NOTIFICATIONS & TOAST */
        .notify-item {{ background: var(--white); padding: 15px; margin-bottom: 10px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 4px solid var(--blue); position: relative; }}
        .notify-item.read {{ border-left-color: #ddd; opacity: 0.7; box-shadow: none; background: #fcfcfc; }}
        .notify-time {{ font-size: 0.75rem; color: #999; position: absolute; top: 15px; right: 15px; }}
        .notify-msg {{ padding-right: 30px; }}
        .notify-dot {{ position: absolute; top: 2px; right: 50%; transform: translateX(50%); width: 10px; height: 10px; background: var(--red); border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 5px rgba(0,0,0,0.2); }}

        #toast-container {{ position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 3000; width: 90%; max-width: 400px; pointer-events: none; }}
        .toast {{ background: #333; color: #fff; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); opacity: 0; transform: translateY(-20px); transition: all 0.3s ease; display: flex; align-items: center; gap: 10px; pointer-events: auto; }}
        .toast.show {{ opacity: 1; transform: translateY(0); }}
        .toast i {{ color: var(--orange); font-size: 1.2rem; }}

        /* NAV & MODAL */
        .bottom-nav {{ position: fixed; bottom: 0; left: 0; width: 100%; background: var(--white); border-top: 1px solid #eee; display: flex; justify-content: space-around; padding: 8px 0; z-index: 500; padding-bottom: max(8px, env(safe-area-inset-bottom)); box-shadow: 0 -2px 10px rgba(0,0,0,0.03); }}
        .nav-item {{ background: none; border: none; color: #aaa; display: flex; flex-direction: column; align-items: center; font-size: 0.7rem; width: 100%; cursor: pointer; position: relative; transition: color 0.2s; gap: 4px; }}
        .nav-item.active {{ color: var(--primary); font-weight: 600; }}
        .nav-item i {{ font-size: 1.4rem; }}

        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 2000; justify-content: center; align-items: flex-end; backdrop-filter: blur(2px); }}
        .modal.active {{ display: flex; animation: slideUp 0.25s ease-out; }}
        .modal-content {{ background: var(--white); width: 100%; max-width: 600px; height: 95vh; border-radius: 20px 20px 0 0; padding: 20px; box-sizing: border-box; display: flex; flex-direction: column; box-shadow: 0 -10px 40px rgba(0,0,0,0.2); position: relative; }}
        .close {{ position: absolute; top: 15px; right: 15px; font-size: 28px; color: #999; cursor: pointer; z-index: 10; padding: 10px; line-height: 1; }}
        @keyframes slideUp {{ from {{ transform: translateY(100%); }} to {{ transform: translateY(0); }} }}
        
        /* IMPROVED EDIT LIST & ITEMS */
        .edit-list {{ flex-grow: 1; overflow-y: auto; margin: 15px 0; border: 1px solid #eee; border-radius: 8px; -webkit-overflow-scrolling: touch; }}
        .edit-item {{ 
            display: grid; 
            grid-template-columns: 1fr auto; 
            gap: 10px; 
            padding: 12px; 
            border-bottom: 1px solid #eee; 
            align-items: center;
        }}
        .edit-item:last-child {{ border-bottom: none; }}
        
        .product-info {{ font-size: 0.95rem; line-height: 1.3; }}
        .product-name {{ font-weight: 600; color: #333; }}
        .product-price {{ font-size: 0.85rem; color: #555; margin-top: 4px; font-weight: 500; }}
        .product-mods {{ font-size: 0.8rem; color: #777; margin-top: 2px; }}

        /* CONTROLS */
        .qty-ctrl-lg {{ display: flex; align-items: center; gap: 8px; background: #f0f0f0; padding: 4px; border-radius: 10px; }}
        .qty-btn-lg {{ 
            width: 36px; height: 36px; border-radius: 8px; border: none; 
            background: #fff; cursor: pointer; font-weight: bold; font-size: 1.2rem; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #333;
            display: flex; align-items: center; justify-content: center;
        }}
        .qty-btn-lg:active {{ transform: scale(0.95); background: #e0e0e0; }}
        .qty-val {{ font-weight: bold; font-size: 1rem; min-width: 24px; text-align: center; }}
        
        .del-btn {{ 
            width: 36px; height: 36px; border-radius: 8px; border: none; 
            background: #fee2e2; color: #c0392b; cursor: pointer; 
            display: flex; align-items: center; justify-content: center;
            margin-left: 5px;
        }}

        .big-btn {{ width: 100%; padding: 16px; background: var(--primary); color: white; border: none; border-radius: 12px; font-size: 1rem; font-weight: bold; margin-top: 15px; cursor: pointer; }}
        .big-btn.danger {{ background: var(--red); }}
        .big-btn.success {{ background: var(--green); }}
        
        /* CUSTOMER EDIT CARD */
        .customer-edit-card {{
            background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
            padding: 15px; margin-bottom: 15px;
        }}
        .collapse-content {{ display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee; }}
        .collapse-content.show {{ display: block; }}
        
        /* MODIFIERS STYLES */
        .mod-list {{ display: flex; flex-direction: column; gap: 5px; }}
        .mod-item {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; cursor: pointer; }}
        .mod-checkbox {{ width: 20px; height: 20px; border: 2px solid #ddd; border-radius: 4px; margin-right: 10px; display: flex; justify-content: center; align-items: center; transition: all 0.2s; }}
        .mod-item.selected .mod-checkbox {{ background: var(--primary); border-color: var(--primary); }}
        .mod-item.selected .mod-checkbox::after {{ content: '✓'; color: white; font-size: 14px; }}
        .mod-info {{ display: flex; align-items: center; }}
        
        #loading-indicator {{ text-align: center; padding: 20px; color: #999; display: none; }}
        #search-input {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; margin-bottom: 10px; box-sizing: border-box; background: #f9f9f9; }}
        #search-input:focus {{ border-color: #333; background: #fff; outline: none; }}
        
        /* FORMS */
        .form-group {{ margin-bottom: 15px; text-align: left; }}
        .form-group label {{ display: block; margin-bottom: 5px; font-weight: 600; color: #555; }}
        .form-control {{ width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #ddd; font-size: 1rem; background:#fff; box-sizing: border-box; }}
        
        /* TRANSACTION TOGGLE */
        .toggle-switch {{ display: flex; background: #eee; border-radius: 10px; padding: 4px; margin-bottom: 15px; }}
        .toggle-option {{ flex: 1; text-align: center; padding: 10px; border-radius: 8px; cursor: pointer; font-weight: 600; color: #666; transition: all 0.2s; }}
        .toggle-option.active.income {{ background: #27ae60; color: white; }}
        .toggle-option.active.expense {{ background: #e74c3c; color: white; }}
    </style>
</head>
<body>
    {content}
    
    <div id="toast-container"></div>

    <div id="delivery-info-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="document.getElementById('delivery-info-modal').classList.remove('active')">&times;</span>
            <h3 style="margin-top:0;">📦 Дані доставки</h3>
            
            <div class="form-group">
                <label>Телефон клієнта</label>
                <input type="tel" id="del-phone" class="form-control" placeholder="0XX XXX XX XX">
            </div>
            
            <div class="form-group">
                <label>Ім'я</label>
                <input type="text" id="del-name" class="form-control" placeholder="Ім'я клієнта">
            </div>
            
            <div class="form-group">
                <label>Адреса</label>
                <textarea id="del-address" class="form-control" rows="2" placeholder="Вулиця, будинок..."></textarea>
            </div>
            
            <div class="form-group">
                <label>Час доставки</label>
                <input type="text" id="del-time" class="form-control" placeholder="Наприклад: 19:30 або 'Якнайшвидше'" value="Якнайшвидше">
            </div>
            
            <div class="form-group">
                <label>Коментар</label>
                <input type="text" id="del-comment" class="form-control" placeholder="Домофон, решта з...">
            </div>

            <button class="big-btn success" onclick="finalizeDeliveryOrder()">🚀 Створити замовлення</button>
        </div>
    </div>

    <div id="staff-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modal-body" style="display: flex; flex-direction: column; height: 100%;"></div>
        </div>
    </div>

    <div id="cancel-modal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="document.getElementById('cancel-modal').classList.remove('active')">&times;</span>
            <h3 style="color:#e74c3c; margin-top:0;">🚫 Скасування замовлення</h3>
            <p>Що робити з продуктами?</p>
            
            <div style="display:flex; flex-direction:column; gap:10px;">
                <button class="big-btn" onclick="submitCancel('return')" style="background:#3498db;">
                    ↩️ Повернути на склад
                    <div style="font-size:0.75em; font-weight:normal;">Клієнт відмовився, страви не готували</div>
                </button>
                
                <button class="big-btn danger" onclick="showWasteOptions()">
                    🗑️ Списати (У смітник)
                    <div style="font-size:0.75em; font-weight:normal;">Страви зіпсовано або вже приготовано</div>
                </button>
            </div>
            
            <div id="waste-options" style="display:none; margin-top:15px; padding-top:15px; border-top:1px solid #eee;">
                <p style="color:#c0392b; font-weight:bold;">Хто платить за продукти?</p>
                <button class="big-btn danger" onclick="submitCancel('waste', true)">
                    💸 Стягнути з працівника
                    <div style="font-size:0.75em; font-weight:normal;">Борг = Собівартість продуктів</div>
                </button>
                <button class="big-btn secondary" onclick="submitCancel('waste', false)">
                    🏢 Витрати закладу
                    <div style="font-size:0.75em; font-weight:normal;">Просто списати</div>
                </button>
            </div>
        </div>
    </div>

    <script>
        let currentView = 'orders'; 
        let currentTableId = null;
        let menuData = [];
        let cart = {{}}; 
        let editingOrderId = null;
        let currentStatusChangeId = null;
        let lastNotificationCount = 0;
        let wakeLock = null;
        let orderMode = 'table';
        
        let selectedProduct = null;
        let selectedModifiers = new Set();

        let ws = null;
        let wsRetryInterval = 1000;

        document.addEventListener('DOMContentLoaded', () => {{
            const activeBtn = document.querySelector('.nav-item.active');
            if (activeBtn) {{
                const onclick = activeBtn.getAttribute('onclick');
                const match = onclick.match(/switchTab\('(\w+)'\)/);
                if (match) currentView = match[1];
            }}
            
            fetchData();
            updateNotifications();
            connectWebSocket();
            setInterval(updateNotifications, 15000); 
            
            document.addEventListener("visibilitychange", async () => {{
                if (document.visibilityState === 'visible') {{
                    requestWakeLock();
                    updateNotifications();
                    if (!ws || ws.readyState === WebSocket.CLOSED) connectWebSocket();
                }}
            }});
            
            document.body.addEventListener('click', initNotifications, {{ once: true }});
        }});

        function connectWebSocket() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Виправлений шлях для WebSocket: /staff/ws
            const wsUrl = `${{protocol}}//${{window.location.host}}/staff/ws`;
            
            if (ws && ws.readyState === WebSocket.OPEN) return;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {{
                console.log("WebSocket Connected");
                wsRetryInterval = 1000; 
                document.getElementById('loading-indicator').style.display = 'none';
            }};

            ws.onmessage = (event) => {{
                try {{
                    const data = JSON.parse(event.data);
                    if (data.type === 'new_order' || data.type === 'order_updated' || data.type === 'item_ready') {{
                        if (data.type === 'new_order') showToast("🔔 " + data.message);
                        else showToast("🔄 Оновлення даних...");
                        fetchData(); 
                        if (editingOrderId && data.order_id == editingOrderId) openOrderEditModal(editingOrderId, true); 
                    }}
                }} catch (e) {{ console.error("WS Parse Error", e); }}
            }};

            ws.onclose = () => {{
                setTimeout(connectWebSocket, wsRetryInterval);
                wsRetryInterval = Math.min(wsRetryInterval * 2, 10000); 
            }};

            ws.onerror = (err) => {{ ws.close(); }};
        }}

        function initNotifications() {{
            if (!("Notification" in window)) return;
            if (Notification.permission === "default") {{
                Notification.requestPermission();
            }}
            requestWakeLock();
        }}

        function sendSystemNotification(text) {{
            if (!("Notification" in window) || Notification.permission !== "granted") return;
            
            // Використовуємо Service Worker для відображення системного PWA-сповіщення
            if ('serviceWorker' in navigator) {{
                navigator.serviceWorker.ready.then(function(registration) {{
                    registration.showNotification("Оновлення замовлень", {{
                        body: text,
                        icon: '/static/favicons/icon-192.png',
                        badge: '/static/favicons/favicon-32x32.png',
                        vibrate: [200, 100, 200, 100, 200],
                        requireInteraction: true // Сповіщення висітиме, поки на нього не клікнуть
                    }});
                }});
            }} else {{
                // Фоллбек для старих браузерів
                try {{ new Notification("Оновлення замовлень", {{ body: text, icon: '/static/favicons/icon-192.png' }}); }} catch (e) {{}}
            }}
        }}

        async function requestWakeLock() {{
            try {{ if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen'); }} catch (err) {{}}
        }}

        function showToast(message) {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.innerHTML = `<i class="fa-solid fa-bell"></i> <span>${{message}}</span>`;
            container.appendChild(toast);
            setTimeout(() => toast.classList.add('show'), 10);
            if (navigator.vibrate) navigator.vibrate(200);
            setTimeout(() => {{ toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }}, 5000);
        }}

        function switchTab(view) {{
            currentView = view;
            document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
            event.currentTarget.classList.add('active');
            if (view === 'notifications') renderNotifications();
            else {{
                document.getElementById('content-area').innerHTML = '';
                document.getElementById('loading-indicator').style.display = 'block';
                fetchData();
            }}
        }}

        async function fetchData() {{
            if (currentView === 'notifications') return;
            try {{
                const response = await fetch(`/staff/api/data?view=${{currentView}}`);
                if (response.status === 401) {{ window.location.href = "/staff/login"; return; }}
                if (!response.ok) throw new Error("Server error");
                const data = await response.json();
                document.getElementById('loading-indicator').style.display = 'none';
                document.getElementById('content-area').innerHTML = data.html;
            }} catch (e) {{ console.error("Fetch error:", e); }}
        }}

        async function updateNotifications() {{
            try {{
                const res = await fetch('/staff/api/notifications');
                if (res.status === 401) return;
                const data = await res.json();
                const badge = document.getElementById('nav-notify-badge');
                window.notificationsList = data.list;
                if (data.unread_count > 0) {{
                    badge.style.display = 'block';
                    if (data.unread_count > lastNotificationCount) {{
                        const newest = data.list[0];
                        if (newest) {{ showToast(newest.message); sendSystemNotification(newest.message); }}
                    }}
                }} else badge.style.display = 'none';
                lastNotificationCount = data.unread_count;
                if (currentView === 'notifications') renderNotifications();
            }} catch(e) {{}}
        }}

        function renderNotifications() {{
            const container = document.getElementById('content-area');
            document.getElementById('loading-indicator').style.display = 'none';
            if (!window.notificationsList || window.notificationsList.length === 0) {{
                container.innerHTML = "<div class='empty-state'><i class='fa-regular fa-bell-slash'></i>Сповіщень немає</div>";
                return;
            }}
            let html = "";
            window.notificationsList.forEach(n => {{
                const cls = n.is_read ? 'read' : '';
                html += `<div class="notify-item ${{cls}}"><div class="notify-msg">${{n.message}}</div><span class="notify-time">${{n.time}}</span></div>`;
            }});
            container.innerHTML = html;
            document.getElementById('nav-notify-badge').style.display = 'none';
        }}

        async function toggleShift() {{
            if(!confirm("Змінити статус зміни?")) return;
            const res = await fetch('/staff/api/shift/toggle', {{ method: 'POST' }});
            if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
            const data = await res.json();
            if (data.status === 'ok') location.reload();
        }}

        async function openOrderEditModal(orderId, keepCart = false) {{
            editingOrderId = orderId;
            const modal = document.getElementById('staff-modal');
            const body = document.getElementById('modal-body');
            
            if(!keepCart) body.innerHTML = '<div style="text-align:center; padding:50px;"><i class="fa-solid fa-spinner fa-spin"></i> Завантаження...</div>';
            
            modal.classList.add('active');
            
            try {{
                const res = await fetch(`/staff/api/order/${{orderId}}/details`);
                if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
                const data = await res.json();
                if(data.error) {{ body.innerHTML = `<div style="text-align:center; padding:20px;"><h3>Помилка</h3><p>${{data.error}}</p></div>`; return; }}
                
                // --- GENERATE COURIER HTML ---
                let courierHtml = "";
                if (data.can_assign_courier && data.is_delivery) {{
                    let courierOptions = '<option value="0">Не призначено</option>';
                    if (data.couriers && data.couriers.length > 0) {{
                        data.couriers.forEach(c => {{
                            courierOptions += `<option value="${{c.id}}" ${{c.selected ? 'selected' : ''}}>${{c.name}}</option>`;
                        }});
                    }} else courierOptions = '<option value="0" disabled>Немає кур\\'єрів на зміні</option>';
                    
                    courierHtml = `<div style="margin-bottom:15px; background:#e3f2fd; padding:10px; border-radius:8px;"><label style="font-size:0.85rem; color:#1565c0; margin-bottom:5px; display:block;">🚚 Кур'єр:</label><select onchange="assignCourier(this.value)" style="width:100%; padding:8px; border-radius:6px; border:1px solid #90caf9; font-weight:bold;">${{courierOptions}}</select></div>`;
                }}

                // --- GENERATE PAYMENT HTML (NEW) ---
                let payStyle = data.payment_method === 'cash' ? 'background:#fff3e0; color:#e67e22;' : 'background:#e3f2fd; color:#2980b9;';
                let payIcon = data.payment_method === 'cash' ? '<i class="fa-solid fa-money-bill-wave"></i>' : '<i class="fa-regular fa-credit-card"></i>';
                let payText = data.payment_method === 'cash' ? 'Готівка' : 'Картка / Термінал';
                let paymentHtml = `<div style="${{payStyle}} padding:10px; border-radius:8px; margin-bottom:10px; font-weight:bold; text-align:center; display:flex; justify-content:center; gap:10px; align-items:center;">
                    ${{payIcon}} <span>${{payText}}</span>
                </div>`;
                
                // --- GENERATE COMMENT HTML (NEW) ---
                let commentHtml = "";
                if (data.comment) {{
                    commentHtml = `<div style="background:#fee2e2; color:#c0392b; padding:10px; border-radius:8px; margin-bottom:15px; font-size:0.95rem; line-height:1.4; border-left: 4px solid #c0392b;">
                        <i class="fa-solid fa-circle-exclamation"></i> <b>Коментар:</b> ${{data.comment}}
                    </div>`;
                }}

                // --- DATA FOR CUSTOMER EDIT CARD ---
                const custName = data.customer_name || '';
                const custPhone = data.phone_number || '';
                const custAddr = data.address || '';
                const custTime = data.delivery_time || 'Якнайшвидше';
                const custComment = data.comment || '';

                const customerHtml = `
                <div class="customer-edit-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;" onclick="document.getElementById('cust-details').classList.toggle('show')">
                        <div>
                            <i class="fa-solid fa-user-pen"></i> <b>${{custName || 'Клієнт'}}</b>
                            <div style="font-size:0.8rem; color:#666;">${{custPhone}}</div>
                        </div>
                        <i class="fa-solid fa-chevron-down" style="color:#999;"></i>
                    </div>
                    
                    <div id="cust-details" class="collapse-content">
                        <div class="form-group">
                            <label>Ім'я</label>
                            <input type="text" id="edit-name" class="form-control" value="${{custName}}">
                        </div>
                        <div class="form-group">
                            <label>Телефон</label>
                            <input type="tel" id="edit-phone" class="form-control" value="${{custPhone}}">
                        </div>
                        <div class="form-group">
                            <label>Адреса</label>
                            <input type="text" id="edit-address" class="form-control" value="${{custAddr}}">
                        </div>
                        <div class="form-group">
                            <label>Час доставки</label>
                            <input type="text" id="edit-time" class="form-control" value="${{custTime}}">
                        </div>
                        <div class="form-group">
                            <label>Коментар (Кухня/Доставка)</label>
                            <textarea id="edit-comment" class="form-control" rows="2" placeholder="Напр: Домофон 25, без цибулі...">${{custComment}}</textarea>
                        </div>
                    </div>
                </div>`;

                if (!keepCart) {{
                    cart = {{}};
                    data.items.forEach(i => {{
                        const key = `exist_${{i.id}}_${{Math.random()}}`;
                        cart[key] = {{ qty: i.qty, id: i.id, name: i.name, price: i.price, modifiers: i.modifiers || [] }}; 
                    }});
                }}

                renderEditCart(data.can_edit_items, data.statuses, courierHtml, customerHtml, data.id, paymentHtml, commentHtml);
                
            }} catch (e) {{ body.innerHTML = "Помилка: " + e.message; }}
        }}

        function renderEditCart(canEdit, statuses, courierHtml, customerHtml, orderIdStr, paymentHtml = "", commentHtml = "") {{
            const body = document.getElementById('modal-body');
            let itemsHtml = `<div class="edit-list">`;
            const currentItems = Object.entries(cart);
            let currentTotal = 0;
            
            if (currentItems.length > 0) {{
                currentItems.forEach(([key, item]) => {{
                    const itemSum = item.price * item.qty;
                    currentTotal += itemSum;
                    
                    let modsText = "";
                    if(item.modifiers && item.modifiers.length > 0) {{
                        modsText = `<div class="product-mods">+ ${{item.modifiers.map(m=>m.name).join(', ')}}</div>`;
                    }}

                    const controls = canEdit ? `
                        <div class="qty-ctrl-lg">
                            <button class="qty-btn-lg" onclick="updateCartItemQty('${{key}}', -1, true)">-</button>
                            <div class="qty-val">${{item.qty}}</div>
                            <button class="qty-btn-lg" onclick="updateCartItemQty('${{key}}', 1, true)">+</button>
                        </div>
                        <button class="del-btn" onclick="updateCartItemQty('${{key}}', -999, true)"><i class="fa-solid fa-trash"></i></button>
                    ` : `<div style="font-weight:bold; font-size:1.1rem;">x${{item.qty}}</div>`;

                    itemsHtml += `
                    <div class="edit-item">
                        <div class="product-info">
                            <div class="product-name">${{item.name}}</div>
                            ${{modsText}}
                            <div class="product-price">${{item.price.toFixed(2)}} x ${{item.qty}} = <b>${{itemSum.toFixed(2)}}</b></div>
                        </div>
                        <div style="display:flex;">${{controls}}</div>
                    </div>`;
                }});
            }} else itemsHtml += `<div style="padding:10px; text-align:center; color:#999;">Кошик порожній</div>`;
            
            itemsHtml += `</div>`;
            
            let statusOptions = "";
            statuses.forEach(s => {{
                statusOptions += `<option value="${{s.id}}" ${{s.selected ? 'selected' : ''}} data-completed="${{s.is_completed}}" data-cancelled="${{s.is_cancelled}}">${{s.name}}</option>`;
            }});
            
            const addBtn = canEdit ? `<button class="action-btn secondary" style="width:100%; margin-bottom:10px;" onclick="openAddProductModal(true)"><i class="fa-solid fa-plus"></i> Додати страву</button>` : '';
            const saveBtn = `<button class="big-btn" onclick="saveOrderChanges()">💾 Зберегти зміни (~${{currentTotal.toFixed(2)}} грн)</button>`;

            body.innerHTML = `
                ${{paymentHtml}}
                ${{commentHtml}}
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0;">Замовлення #${{orderIdStr}}</h3>
                    <div style="font-size:1.2rem; font-weight:bold;">${{currentTotal.toFixed(2)}} грн</div>
                </div>
                ${{statusOptions ? `
                <div style="margin-bottom:15px; background:#f9f9f9; padding:10px; border-radius:8px;">
                    <select id="status-select" style="width:100%; padding:10px; border-radius:6px; border:1px solid #ddd; background:#fff; font-size:1rem; font-weight:bold;" onchange="changeOrderStatus(this)">
                        ${{statusOptions}}
                    </select>
                </div>` : ''}}
                ${{courierHtml}}
                ${{customerHtml}}
                <h4 style="margin:10px 0 5px 0;">Склад замовлення:</h4>
                ${{itemsHtml}}
                ${{addBtn}}
                ${{saveBtn}}
            `;
        }}

        async function assignCourier(courierId) {{
            if(!confirm("Змінити кур'єра?")) return;
            try {{
                const res = await fetch('/staff/api/order/assign_courier', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ orderId: editingOrderId, courierId: courierId }})
                }});
                const data = await res.json();
                if(data.success) showToast(data.message); else alert(data.error);
            }} catch(e) {{ alert("Помилка з'єднання"); }}
        }}

        function updateCartItemQty(key, delta, isEditing = false) {{
            if (cart[key]) {{
                cart[key].qty += delta;
                if (cart[key].qty <= 0) delete cart[key];
                
                if(isEditing) {{
                    openOrderEditModal(editingOrderId, true); 
                }} else {{
                    renderNewOrderMenu(); 
                }}
            }}
        }}

        async function changeOrderStatus(selectElem) {{
            const newStatusId = selectElem.value;
            const option = selectElem.options[selectElem.selectedIndex];
            
            const isCancelled = option.getAttribute('data-cancelled') === 'true';
            
            if (isCancelled) {{
                document.getElementById('cancel-modal').classList.add('active');
                selectElem.value = ""; 
                return;
            }}

            const isCompleted = option.getAttribute('data-completed') === 'true';
            if (isCompleted) {{
                currentStatusChangeId = newStatusId;
                document.getElementById('modal-body').innerHTML = `
                    <div style="flex-grow:1; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                        <h3 style="text-align:center;">💰 Оплата замовлення</h3>
                        <p style="text-align:center; color:#666; margin-bottom:20px;">Оберіть метод оплати:</p>
                        <button class="big-btn" style="background:#27ae60; margin-bottom:10px;" onclick="finishStatusChange('cash')"><i class="fa-solid fa-money-bill-wave"></i> Готівка</button>
                        <button class="big-btn" style="background:#2980b9;" onclick="finishStatusChange('card')"><i class="fa-regular fa-credit-card"></i> Картка / Термінал</button>
                        <br><button class="action-btn secondary" style="width:100%; margin-top:10px; justify-content:center;" onclick="openOrderEditModal(editingOrderId, true)">Скасувати</button>
                    </div>
                `;
                return;
            }}
            await updateStatusAPI(newStatusId, null);
        }}

        async function finishStatusChange(method) {{
            await updateStatusAPI(currentStatusChangeId, method);
            closeModal(); fetchData();
        }}

        async function updateStatusAPI(statusId, paymentMethod) {{
            const res = await fetch('/staff/api/order/update_status', {{
                method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ orderId: editingOrderId, statusId: statusId, paymentMethod: paymentMethod }})
            }});
            if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
            const data = await res.json();
            if(data.error) alert(data.error); else showToast("Статус оновлено");
        }}

        async function saveOrderChanges() {{
            const btn = event.currentTarget;
            btn.disabled = true;
            btn.innerText = "Збереження...";

            try {{
                // 1. Оновлення деталей клієнта (Ім'я, Адреса, Комент)
                const detailsPayload = {{
                    orderId: editingOrderId,
                    name: document.getElementById('edit-name').value,
                    phone: document.getElementById('edit-phone').value,
                    address: document.getElementById('edit-address').value,
                    delivery_time: document.getElementById('edit-time').value,
                    comment: document.getElementById('edit-comment').value
                }};

                await fetch('/staff/api/order/update_details', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(detailsPayload)
                }});

                // 2. Оновлення кошика
                const items = Object.values(cart);
                const res = await fetch('/staff/api/order/update_items', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ orderId: editingOrderId, items: items }})
                }});
                
                const data = await res.json();
                if(data.success) {{
                    showToast("Успішно збережено! ✅");
                    closeModal();
                    fetchData();
                }} else {{
                    alert("Помилка збереження товарів: " + data.error);
                }}
            }} catch (e) {{
                alert("Помилка з'єднання");
            }} finally {{
                btn.disabled = false;
                btn.innerText = "💾 Зберегти зміни";
            }}
        }}

        // --- NEW: Логика модалки отмены ---
        function showWasteOptions() {{
            document.getElementById('waste-options').style.display = 'block';
        }}

        async function submitCancel(type, penalty = false) {{
            if(!confirm("Підтвердити скасування?")) return;
            
            try {{
                const res = await fetch('/staff/api/order/cancel_complex', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        orderId: editingOrderId,
                        actionType: type,
                        applyPenalty: penalty,
                        reason: type === 'return' ? 'Повернення на склад' : (penalty ? 'Списання (Борг)' : 'Списання (Заклад)')
                    }})
                }});
                
                const data = await res.json();
                if(data.success) {{
                    showToast(data.message);
                    document.getElementById('cancel-modal').classList.remove('active');
                    closeModal(); 
                    fetchData();
                }} else {{
                    alert("Помилка: " + data.error);
                }}
            }} catch(e) {{ alert("Помилка з'єднання"); }}
        }}

        // --- NEW ORDER & PRODUCT ADDING LOGIC ---
        function startDeliveryCreation() {{
            orderMode = 'delivery';
            cart = {{}};
            document.getElementById('staff-modal').classList.add('active');
            openAddProductModal(false);
        }}

        async function openAddProductModal(isEditing = false) {{
            if (menuData.length === 0) {{
                document.getElementById('modal-body').innerHTML = '<div style="text-align:center; padding:20px;">Завантаження меню...</div>';
                const res = await fetch('/staff/api/menu/full');
                if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
                menuData = (await res.json()).menu;
            }}
            renderProductList("", isEditing);
        }}
        
        function renderProductList(filterText = "", isEditing = false) {{
            const body = document.getElementById('modal-body');
            const lowerFilter = filterText.toLowerCase();
            
            let backFn;
            let titleText;
            
            if (isEditing) {{
                backFn = `openOrderEditModal(${{editingOrderId}}, true)`;
                titleText = 'Додати страву';
            }} else if (orderMode === 'delivery') {{
                backFn = `closeModal()`; 
                titleText = 'Нова доставка';
            }} else {{
                backFn = `openTableModal(${{currentTableId}}, '${{document.getElementById('modal-title')?.innerText || ''}}')`;
                titleText = 'Нове замовлення';
            }}

            let html = `
                <div style="display:flex;justify-content:space-between;align-items:center; margin-bottom:10px;">
                    <h3 style="margin:0;">${{titleText}}</h3>
                    <button onclick="${{backFn}}" class="action-btn secondary" style="padding:5px 10px;">Назад</button>
                </div>
                <input type="text" id="search-input" placeholder="🔍 Пошук..." value="${{filterText}}" oninput="renderProductList(this.value, ${{isEditing}})">
                <div class="edit-list">`;
                
            let hasItems = false;
            menuData.forEach(cat => {{
                const filteredProds = cat.products.filter(p => p.name.toLowerCase().includes(lowerFilter));
                if (filteredProds.length > 0) {{
                    hasItems = true;
                    html += `<div style="background:#eee; padding:8px 12px; font-weight:bold; font-size:0.9rem; position:sticky; top:0;">${{cat.name}}</div>`;
                    filteredProds.forEach(p => {{
                        const pData = JSON.stringify(p).replace(/"/g, '&quot;');
                        html += `
                        <div class="edit-item">
                            <div style="flex-grow:1;">${{p.name}} <small>(${{p.price}} грн)</small></div>
                            <button class="action-btn" style="padding:6px 12px;" onclick="handleProductClick(this)" data-product="${{pData}}" data-editing="${{isEditing}}">+</button>
                        </div>`;
                    }});
                }}
            }});
            if(!hasItems) html += `<div style="padding:20px; text-align:center; color:#999;">Нічого не знайдено</div>`;
            html += `</div>`;
            
            if(!isEditing) {{
                 const count = Object.keys(cart).length;
                 const total = Object.values(cart).reduce((sum, i) => sum + i.price * i.qty, 0);
                 if (count > 0) {{
                     if (orderMode === 'delivery') {{
                         html += `<button class="big-btn" onclick="openDeliveryInfoModal()">➡️ Далі (${{total.toFixed(2)}} грн)</button>`;
                     }} else {{
                         html += `<button class="big-btn" onclick="submitNewOrder()">✅ Замовити (${{count}} поз. - ${{total.toFixed(2)}} грн)</button>`;
                     }}
                 }}
            }}

            body.innerHTML = html;
            const input = document.getElementById('search-input');
            if(input) {{ input.focus(); input.value = ''; input.value = filterText; }}
        }}

        window.handleProductClick = (btn) => {{
            const product = JSON.parse(btn.dataset.product);
            const isEditing = btn.dataset.editing === 'true';
            
            if (product.modifiers && product.modifiers.length > 0) {{
                openModifierModal(product, isEditing);
            }} else {{
                addToCart(product, [], isEditing);
            }}
        }};

        function openModifierModal(product, isEditing) {{
            selectedProduct = product;
            selectedModifiers.clear();
            
            const body = document.getElementById('modal-body');
            let modListHtml = `<div class="mod-list" style="overflow-y:auto; max-height:300px; margin:10px 0;">`;
            
            product.modifiers.forEach(mod => {{
                modListHtml += `
                <div class="mod-item" onclick="toggleStaffMod(${{mod.id}}, this)">
                    <div class="mod-info">
                        <div class="mod-checkbox"></div> <span>${{mod.name}}</span>
                    </div>
                    <b>+${{mod.price}} грн</b>
                </div>`;
            }});
            modListHtml += `</div>`;
            
            body.innerHTML = `
                <h3 style="text-align:center; margin-top:0;">${{product.name}}</h3>
                <p style="text-align:center; color:#666;">Оберіть добавки:</p>
                ${{modListHtml}}
                <div style="margin-top:auto; padding-top:10px; border-top:1px solid #eee;">
                    <button class="big-btn" id="staff-mod-add-btn" onclick="addStaffWithMods(${{isEditing}})">Додати (<span>${{product.price}}</span> грн)</button>
                    <button class="action-btn secondary" style="width:100%; margin-top:10px; justify-content:center;" onclick="renderProductList('', ${{isEditing}})">Скасувати</button>
                </div>
            `;
        }}

        window.toggleStaffMod = (id, row) => {{
            if(selectedModifiers.has(id)) {{
                selectedModifiers.delete(id);
                row.classList.remove('selected');
            }} else {{
                selectedModifiers.add(id);
                row.classList.add('selected');
            }}
            updateStaffModPrice();
        }};

        function updateStaffModPrice() {{
            let total = selectedProduct.price;
            selectedProduct.modifiers.forEach(m => {{
                if(selectedModifiers.has(m.id)) total += m.price;
            }});
            const btnSpan = document.querySelector('#staff-mod-add-btn span');
            if(btnSpan) btnSpan.innerText = total.toFixed(2);
        }}

        window.addStaffWithMods = (isEditing) => {{
            const mods = [];
            selectedProduct.modifiers.forEach(m => {{
                if(selectedModifiers.has(m.id)) mods.push(m);
            }});
            addToCart(selectedProduct, mods, isEditing);
        }};

        function addToCart(product, modifiers, isEditing) {{
            const modIds = modifiers.map(m => m.id).sort().join('-');
            const key = `${{product.id}}-${{modIds}}`;
            
            if (cart[key]) {{
                cart[key].qty++;
            }} else {{
                let unitPrice = product.price;
                modifiers.forEach(m => unitPrice += m.price);
                
                let displayName = product.name;
                if (modifiers.length > 0) {{
                    displayName += ` (+ ${{modifiers.map(m => m.name).join(', ')}})`;
                }}

                cart[key] = {{
                    id: product.id, 
                    name: displayName,
                    price: unitPrice,
                    qty: 1,
                    modifiers: modifiers
                }};
            }}
            
            if (isEditing) {{
                openOrderEditModal(editingOrderId, true);
            }} else {{
                renderProductList("", false);
                showToast("Додано!");
            }}
        }}

        function openTableModal(tableId, tableName) {{
            currentTableId = tableId;
            orderMode = 'table'; 
            cart = {{}};
            const modal = document.getElementById('staff-modal');
            document.getElementById('modal-body').innerHTML = `
                <h3 style="text-align:center;" id="modal-title">${{tableName}}</h3>
                <div style="flex-grow:1; display:flex; flex-direction:column; justify-content:center; gap:15px;">
                    <button class="big-btn" onclick="openAddProductModal(false)">📝 Нове замовлення</button>
                    <button class="action-btn secondary" style="justify-content:center; padding:15px;" onclick="closeModal()">Закрити</button>
                </div>
            `;
            modal.classList.add('active');
        }}
        
        // Новая функция: Открыть форму доставки
        function openDeliveryInfoModal() {{
            closeModal(); 
            document.getElementById('delivery-info-modal').classList.add('active');
        }}

        // Новая функция: Отправка доставки на сервер
        async function finalizeDeliveryOrder() {{
            const phone = document.getElementById('del-phone').value;
            const name = document.getElementById('del-name').value;
            const address = document.getElementById('del-address').value;
            const comment = document.getElementById('del-comment').value;
            const time = document.getElementById('del-time').value;
            
            if (!phone || !address) return alert("Телефон та Адреса обов'язкові!");
            const items = Object.values(cart);
            
            const btn = event.currentTarget;
            btn.disabled = true;
            btn.innerText = "Створення...";
            
            try {{
                const res = await fetch('/staff/api/order/create_delivery', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        name: name,
                        phone: phone,
                        address: address,
                        comment: comment,
                        delivery_time: time,
                        cart: items
                    }})
                }});
                
                const data = await res.json();
                if(data.success) {{
                    document.getElementById('delivery-info-modal').classList.remove('active');
                    showToast("Доставка створена!");
                    // Очистка формы
                    document.getElementById('del-phone').value = '';
                    document.getElementById('del-name').value = '';
                    document.getElementById('del-address').value = '';
                    document.getElementById('del-comment').value = '';
                    document.getElementById('del-time').value = 'Якнайшвидше';
                    
                    fetchData();
                }} else {{
                    alert("Помилка: " + data.error);
                }}
            }} catch (e) {{
                alert("Помилка з'єднання");
            }} finally {{
                btn.disabled = false;
                btn.innerText = "🚀 Створити замовлення";
            }}
        }}
        
        async function submitNewOrder() {{
            const items = Object.values(cart);
            if(items.length === 0) return alert("Кошик порожній");
            
            const btn = event.currentTarget;
            btn.disabled = true;
            btn.innerText = "Створення...";
            
            try {{
                const res = await fetch('/staff/api/order/create', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ tableId: currentTableId, cart: items }})
                }});
                if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
                
                closeModal();
                fetchData();
                showToast("Замовлення створено");
            }} catch (e) {{
                alert("Помилка створення");
                btn.disabled = false;
            }}
        }}

        function performAction(action, orderId, extra=null) {{
            if(action === 'chef_ready' && !confirm("Підтвердити готовність?")) return;
            fetch('/staff/api/action', {{
                method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ action, orderId, extra }})
            }}).then(res => {{
                if (res.status === 401) {{ window.location.href = "/staff/login"; return; }}
                return res.json();
            }}).then(data => {{
                if(data && data.success) fetchData();
                else if (data) alert("Помилка: " + (data.error || "Unknown"));
            }});
        }}

        function closeModal() {{
            document.getElementById('staff-modal').classList.remove('active');
        }}
        
        function renderNewOrderMenu() {{
             renderProductList("", false);
        }}

        // --- CASHIER FUNCTIONS ---

        async function cashierAction(action, extraId = null) {{
            let payload = {{ action: action }};
            
            if (action === 'open_shift') {{
                const amount = document.getElementById('start-cash-input').value;
                payload.start_cash = amount;
            }} else if (action === 'close_shift') {{
                const actual = prompt("Введіть фактичну суму готівки в касі для закриття:");
                if (actual === null) return;
                payload.actual_cash = actual;
            }} else if (action === 'accept_debt') {{
                if (!confirm("Підтвердити отримання грошей?")) return;
                payload.target_id = extraId;
            }}

            try {{
                const res = await fetch('/staff/api/cashier/action', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});
                const data = await res.json();
                if (data.success) {{
                    showToast(data.message);
                    fetchData();
                }} else {{
                    alert("Помилка: " + data.error);
                }}
            }} catch (e) {{ alert("Помилка з'єднання"); }}
        }}

        // --- IMPROVED TRANSACTION MODAL ---
        function openTransactionModal() {{
            const modal = document.getElementById('staff-modal');
            const body = document.getElementById('modal-body');
            
            let html = `
                <h3 style="margin-top:0; text-align:center;">💸 Нова транзакція</h3>
                
                <div class="toggle-switch">
                    <div class="toggle-option active income" onclick="toggleTransType(this, 'in')">📥 Внесення</div>
                    <div class="toggle-option" onclick="toggleTransType(this, 'out')">📤 Витрата</div>
                </div>
                <input type="hidden" id="trans-type" value="in">
                
                <div class="form-group">
                    <label>Сума (грн)</label>
                    <input type="number" id="trans-amount" class="form-control" placeholder="0.00" style="font-size:1.5rem; text-align:center;">
                </div>
                
                <div class="form-group">
                    <label>Коментар</label>
                    <input type="text" id="trans-comment" class="form-control" placeholder="Опис операції...">
                </div>
                
                <div style="display:flex; gap:10px; margin-bottom:20px; overflow-x:auto;">
                    <button class="action-btn secondary" style="font-size:0.8rem;" onclick="setTransComment('Розмін')">Розмін</button>
                    <button class="action-btn secondary" style="font-size:0.8rem;" onclick="setTransComment('Інкасація')">Інкасація</button>
                    <button class="action-btn secondary" style="font-size:0.8rem;" onclick="setTransComment('Закупівля')">Закупівля</button>
                </div>
                
                <button class="big-btn success" onclick="submitTransaction()">✅ Провести</button>
                <button class="action-btn secondary" style="width:100%; margin-top:10px; justify-content:center;" onclick="closeModal()">Скасувати</button>
            `;
            
            body.innerHTML = html;
            modal.classList.add('active');
            setTimeout(() => document.getElementById('trans-amount').focus(), 100);
        }}
        
        function toggleTransType(el, type) {{
            document.querySelectorAll('.toggle-option').forEach(e => e.classList.remove('active', 'income', 'expense'));
            document.getElementById('trans-type').value = type;
            
            el.classList.add('active');
            if(type === 'in') el.classList.add('income');
            else el.classList.add('expense');
        }}
        
        function setTransComment(text) {{
            document.getElementById('trans-comment').value = text;
        }}
        
        async function submitTransaction() {{
            const type = document.getElementById('trans-type').value;
            const amount = parseFloat(document.getElementById('trans-amount').value);
            const comment = document.getElementById('trans-comment').value;
            
            if(!amount || amount <= 0) return alert("Введіть коректну суму");
            if(!comment) return alert("Введіть коментар");
            
            try {{
                const res = await fetch('/staff/api/cashier/action', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        action: 'transaction',
                        type: type,
                        amount: amount,
                        comment: comment
                    }})
                }});
                const data = await res.json();
                if(data.success) {{ showToast("Транзакція успішна"); fetchData(); closeModal(); }}
                else alert(data.error);
            }} catch(e) {{ alert("Error"); }}
        }}

        // --- SUPPLY MODAL LOGIC ---
        let supplyData = null;
        let supplyCart = [];

        async function openSupplyModal() {{
            const modal = document.getElementById('staff-modal');
            document.getElementById('modal-body').innerHTML = '<div style="text-align:center; padding:30px;"><i class="fa-solid fa-spinner fa-spin"></i> Завантаження довідників...</div>';
            modal.classList.add('active');
            
            try {{
                const res = await fetch('/staff/api/cashier/suppliers');
                supplyData = await res.json();
                supplyCart = []; // Clear cart
                renderSupplyForm();
            }} catch(e) {{
                document.getElementById('modal-body').innerText = "Помилка завантаження";
            }}
        }}

        function renderSupplyForm(filterText = "") {{
            let supOpts = supplyData.suppliers.map(s => `<option value="${{s.id}}">${{s.name}}</option>`).join('');
            let whOpts = supplyData.warehouses.map(w => `<option value="${{w.id}}">${{w.name}}</option>`).join('');
            
            // Filter ingredients
            const lowerFilter = filterText.toLowerCase();
            let ingListHtml = "";
            supplyData.ingredients.forEach(i => {{
                if(i.name.toLowerCase().includes(lowerFilter)) {{
                    ingListHtml += `
                    <div class="edit-item" style="padding:10px;">
                        <div style="flex-grow:1;">${{i.name}} <small>(${{i.unit}})</small></div>
                        <button class="action-btn" style="padding:5px 10px;" onclick="promptAddSupplyItem(${{i.id}}, '${{i.name.replace(/'/g, "\\'")}}')">+</button>
                    </div>`;
                }}
            }});
            if(!ingListHtml) ingListHtml = "<div style='text-align:center; color:#999; padding:10px;'>Нічого не знайдено</div>";

            const body = document.getElementById('modal-body');
            // Check if we are re-rendering just list or full form
            if(!document.getElementById('supply-ing-list-container')) {{
                body.innerHTML = `
                    <h3 style="margin:0 0 10px 0;">📥 Прихід товару</h3>
                    
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:10px;">
                        <div>
                            <label style="font-size:0.8rem; color:#666;">Постачальник</label>
                            <select id="sup-select" style="width:100%; padding:8px; border-radius:8px; border:1px solid #ddd;">${{supOpts}}</select>
                        </div>
                        <div>
                            <label style="font-size:0.8rem; color:#666;">Склад</label>
                            <select id="wh-select" style="width:100%; padding:8px; border-radius:8px; border:1px solid #ddd;">${{whOpts}}</select>
                        </div>
                    </div>

                    <input type="text" id="supply-search" placeholder="🔍 Пошук товару..." value="${{filterText}}" 
                           oninput="renderSupplyForm(this.value)" 
                           style="width:100%; padding:10px; border-radius:8px; border:1px solid #ddd; margin-bottom:5px;">
                    
                    <div id="supply-ing-list-container" class="edit-list" style="height:150px; min-height:150px; background:#f9f9f9;">${{ingListHtml}}</div>

                    <h4 style="margin:10px 0 5px;">Обрано:</h4>
                    <div id="supply-cart-container" class="edit-list" style="height:120px; min-height:120px;"></div>

                    <button class="big-btn success" onclick="submitSupply()">✅ Провести накладну</button>
                    <button class="action-btn secondary" style="width:100%; margin-top:10px; justify-content:center;" onclick="closeModal()">Скасувати</button>
                `;
            }} else {{
                document.getElementById('supply-ing-list-container').innerHTML = ingListHtml;
                // Refocus search input if needed
                const input = document.getElementById('supply-search');
                input.focus();
            }}
            renderSupplyCart();
        }}

        function promptAddSupplyItem(id, name) {{
            const qty = prompt(`Кількість для "${{name}}":`);
            if(!qty) return;
            const price = prompt(`Ціна за одиницю (опціонально):`, "0");
            
            supplyCart.push({{ id, name, qty: parseFloat(qty), price: parseFloat(price)||0 }});
            renderSupplyCart();
        }}

        function renderSupplyCart() {{
            const container = document.getElementById('supply-cart-container');
            if(!container) return;
            
            if(supplyCart.length === 0) {{
                container.innerHTML = "<div style='text-align:center; padding:20px; color:#999;'>Список порожній</div>";
                return;
            }}
            
            let html = "";
            supplyCart.forEach((item, idx) => {{
                html += `
                <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #eee; align-items:center;">
                    <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:60%;">${{item.name}}</div>
                    <div>
                        <b>${{item.qty}}</b> x ${{item.price}} 
                        <button onclick="supplyCart.splice(${{idx}},1); renderSupplyCart();" style="border:none; background:none; color:red; margin-left:5px;">×</button>
                    </div>
                </div>`;
            }});
            container.innerHTML = html;
        }}

        async function submitSupply() {{
            if(supplyCart.length === 0) return alert("Список товарів порожній");
            if(!confirm("Створити накладну?")) return;
            
            const supplierId = document.getElementById('sup-select').value;
            const warehouseId = document.getElementById('wh-select').value;
            
            const items = supplyCart.map(i => ({{ ingredient_id: i.id, qty: i.qty, price: i.price }}));
            
            try {{
                const res = await fetch('/staff/api/cashier/supply', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        supplier_id: supplierId,
                        warehouse_id: warehouseId,
                        items: items,
                        comment: "Мобільна накладна"
                    }})
                }});
                const data = await res.json();
                if(data.success) {{ showToast("Прихід проведено!"); closeModal(); }}
                else alert(data.error);
            }} catch(e) {{ alert("Error"); }}
        }}
        
        // --- PAY DOC MODAL ---
        function openPayDocModal(docId, debtAmount, supplierName) {{
            const modal = document.getElementById('staff-modal');
            document.getElementById('modal-body').innerHTML = `
                <h3 style="text-align:center;">Оплата накладної #${{docId}}</h3>
                <p style="text-align:center; color:#666;">${{supplierName}}</p>
                
                <div class="form-group">
                    <label>Сума до сплати (Борг: ${{debtAmount.toFixed(2)}})</label>
                    <input type="number" id="pay-doc-amount" class="form-control" value="${{debtAmount}}" style="font-size:1.5rem; text-align:center;">
                </div>
                
                <button class="big-btn" onclick="submitDocPayment(${{docId}})">💸 Оплатити з каси</button>
                <button class="action-btn secondary" style="width:100%; margin-top:10px; justify-content:center;" onclick="closeModal()">Скасувати</button>
            `;
            modal.classList.add('active');
        }}
        
        async function submitDocPayment(docId) {{
            const amount = parseFloat(document.getElementById('pay-doc-amount').value);
            if(!amount || amount <= 0) return alert("Невірна сума");
            
            if(!confirm(`Видати з каси ${{amount}} грн?`)) return;
            
            try {{
                const res = await fetch('/staff/api/cashier/pay_doc', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ doc_id: docId, amount: amount }})
                }});
                const data = await res.json();
                if(data.success) {{ showToast("Оплачено!"); closeModal(); fetchData(); }}
                else alert(data.error);
            }} catch(e) {{ alert("Error"); }}
        }}
    </script>
</body>
</html>
"""

# --- ШАБЛОН КАРТКИ СТОЛИКА ---
# ТУТ ОДИНАРНІ ДУЖКИ { } ДЛЯ ФОРМАТУВАННЯ В PYTHON
STAFF_TABLE_CARD = """
<div class="card table-card" onclick="openTableModal({id}, '{name_esc}')" style="border: 2px solid {border_color}; background: {bg_color};">
    <div class="card-title"><i class="fa-solid fa-chair"></i> {name_esc}</div>
    <div class="badge {badge_class}">{status_text}</div>
</div>
"""

# --- ШАБЛОН КАРТКИ ЗАМОВЛЕННЯ ---
# ТУТ ОДИНАРНІ ДУЖКИ { } ДЛЯ ФОРМАТУВАННЯ В PYTHON
STAFF_ORDER_CARD = """
<div class="order-card" id="order-{id}" style="border-left-color: {color}">
    <div class="card-header">
        <div class="order-id">#{id} <span style="font-weight:normal; font-size:0.8rem; color:#999; margin-left:5px;">{time}</span></div>
        <span class="badge {badge_class}">{status}</span>
    </div>
    <div class="card-body" onclick="openOrderEditModal({id})">
        {content}
    </div>
    <div class="card-footer">
        {buttons}
    </div>
</div>
"""