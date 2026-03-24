# tpl_client_qr.py

IN_HOUSE_MENU_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{site_title} - {table_name}</title>
    
    <meta name="description" content="{seo_description}">
    <meta name="keywords" content="{seo_keywords}">
    
    <meta property="og:type" content="website">
    <meta property="og:title" content="{site_title} - {table_name}">
    <meta property="og:description" content="{seo_description}">
    <meta property="og:image" content="/{header_image_url}">
    <meta property="og:site_name" content="{site_title}">
    
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{site_title} - {table_name}">
    <meta name="twitter:description" content="{seo_description}">
    <meta name="twitter:image" content="/{header_image_url}">

    <meta name="robots" content="noindex, nofollow">
    
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family={font_family_serif_encoded}:wght@400;600;700&family={font_family_sans_encoded}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
      :root {{
        /* --- COPY FROM WEB TEMPLATE --- */
        --primary: {primary_color_val};
        --secondary: {secondary_color_val};
        --bg-color: {background_color_val};
        --text-main: {text_color_val};
        --footer-bg: {footer_bg_color_val};
        --footer-text: {footer_text_color_val};
        --nav-bg: {category_nav_bg_color};
        --nav-text: {category_nav_text_color};
        --header-img: url('/{header_image_url}');
        
        --surface: #ffffff;
        --surface-glass: rgba(255, 255, 255, 0.95);
        --border-light: rgba(0, 0, 0, 0.08);
        
        --shadow-sm: 0 4px 12px rgba(0,0,0,0.05);
        --shadow-md: 0 12px 30px rgba(0,0,0,0.08);
        --shadow-lg: 0 20px 60px rgba(0,0,0,0.15);
        --shadow-float: 0 15px 35px rgba(0,0,0,0.2);
        
        --radius-lg: 24px;
        --radius-md: 16px;
        --radius-sm: 10px;
        
        --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
        --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
        
        --font-sans: '{font_family_sans_val}', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        --font-serif: '{font_family_serif_val}', serif;

        /* QR Specific Colors */
        --st-new-bg: #e0f2fe; --st-new-text: #0284c7;
        --st-work-bg: #fff7ed; --st-work-text: #ea580c;
        --st-ready-bg: #dcfce7; --st-ready-text: #16a34a;
        --st-done-bg: #f1f5f9; --st-done-text: #64748b;
      }}
      
      html {{ scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }}
      * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; outline: none; }}
      
      body {{
        margin: 0; background-color: var(--bg-color);
        background-image: 
            radial-gradient(at 0% 0%, color-mix(in srgb, var(--primary), transparent 97%), transparent 60%),
            radial-gradient(at 100% 100%, color-mix(in srgb, var(--secondary), transparent 97%), transparent 60%);
        background-attachment: fixed;
        color: var(--text-main); font-family: var(--font-sans);
        display: flex; flex-direction: column; min-height: 100vh;
        -webkit-font-smoothing: antialiased; font-size: 15px; line-height: 1.5;
      }}

      h1, h2, h3, h4, .serif {{ font-family: var(--font-serif); margin: 0; color: var(--text-main); }}
      button, input, textarea, select {{ font-family: var(--font-sans); }}

      /* --- HEADER (MATCH WEB) --- */
      header {{
          position: relative; height: 35vh; min-height: 280px; max-height: 400px;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          text-align: center; color: white; border-radius: 0 0 50px 50px;
          overflow: hidden; box-shadow: 0 10px 50px rgba(0,0,0,0.15); margin-bottom: 20px;
      }}
      .header-bg {{
          position: absolute; inset: 0; background-image: var(--header-img);
          background-size: cover; background-position: center; z-index: 0; transition: transform 10s ease;
      }}
      header:hover .header-bg {{ transform: scale(1.05); }}
      header::after {{
          content: ''; position: absolute; inset: 0;
          background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
          z-index: 1; backdrop-filter: blur(1px);
      }}
      .header-content {{ position: relative; z-index: 2; width: 90%; max-width: 800px; animation: fadeUp 1s var(--ease-out); }}
      .header-logo {{ height: 110px; width: auto; margin-bottom: 20px; filter: drop-shadow(0 10px 25px rgba(0,0,0,0.3)); transition: transform 0.3s ease; }}
      .header-logo:hover {{ transform: scale(1.05) rotate(-2deg); }}
      header h1 {{ font-size: clamp(2.2rem, 6vw, 4rem); font-weight: 700; text-shadow: 0 4px 25px rgba(0,0,0,0.4); line-height: 1.1; letter-spacing: -0.02em; color: white; }}
      
      .table-badge {{
          display: inline-block; background: rgba(255,255,255,0.25); backdrop-filter: blur(10px);
          padding: 8px 18px; border-radius: 30px; font-size: 1rem; margin-top: 15px; font-weight: 600;
          border: 1px solid rgba(255,255,255,0.4); box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      }}

      /* --- NAVIGATION --- */
      .category-nav-wrapper {{ position: sticky; top: 15px; z-index: 90; display: flex; justify-content: center; padding: 0 15px; margin-bottom: 40px; }}
      .category-nav {{
          display: flex; gap: 8px; overflow-x: auto; padding: 8px; border-radius: 100px;
          background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(20px);
          border: 1px solid rgba(255,255,255,0.6); box-shadow: var(--shadow-md);
          scrollbar-width: none; max-width: 100%;
      }}
      .category-nav::-webkit-scrollbar {{ display: none; }}
      .category-nav a {{
          color: var(--nav-text); text-decoration: none; padding: 10px 24px;
          border-radius: 50px; font-weight: 600; white-space: nowrap; font-size: 0.95rem;
          transition: all 0.3s var(--ease-out); border: 1px solid transparent;
      }}
      .category-nav a.active {{ background: var(--primary); color: white; box-shadow: 0 4px 15px color-mix(in srgb, var(--primary), transparent 60%); }}

      /* --- MAIN --- */
      .container {{ max-width: 1280px; margin: 0 auto; padding: 0 25px; }}
      .category-section {{ margin-bottom: 60px; scroll-margin-top: 120px; }}
      .category-title {{ font-size: 2rem; margin-bottom: 30px; font-weight: 800; display: flex; align-items: center; gap: 20px; letter-spacing: -0.03em; }}
      .category-title::after {{ content: ''; height: 2px; background: var(--secondary); flex-grow: 1; opacity: 0.3; border-radius: 2px; }}

      /* --- GRID & CARDS --- */
      .products-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 30px; }}
      @media (min-width: 1200px) {{ .products-grid {{ grid-template-columns: repeat(4, 1fr); }} }}
      @media (min-width: 1600px) {{ .products-grid {{ grid-template-columns: repeat(5, 1fr); }} }}
      
      .product-card {{
          background: var(--surface); border-radius: var(--radius-md); overflow: hidden; display: flex; flex-direction: column;
          box-shadow: var(--shadow-sm); border: 1px solid var(--border-light); transition: all 0.4s var(--ease-out);
          height: 100%; position: relative; cursor: pointer;
      }}
      .product-card:hover {{ transform: translateY(-8px) scale(1.01); box-shadow: var(--shadow-lg); border-color: color-mix(in srgb, var(--primary), transparent 80%); }}
      
      .product-image-wrapper {{ width: 100%; aspect-ratio: 4/3; overflow: hidden; background: #f5f5f7; }}
      .product-image {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.6s var(--ease-out); }}
      .product-card:hover .product-image {{ transform: scale(1.1); }}
      
      .product-info {{ padding: 20px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }}
      .product-name {{ font-size: 1.2rem; font-weight: 700; margin: 0 0 8px; line-height: 1.3; color: var(--text-main); }}
      .product-desc {{ font-size: 0.9rem; color: #64748b; line-height: 1.5; margin-bottom: 15px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
      .product-footer {{ display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 15px; border-top: 1px solid var(--border-light); }}
      .product-price {{ font-size: 1.25rem; font-weight: 800; color: var(--text-main); }}
      
      .add-btn {{
          background: var(--primary); color: white; border: none; padding: 10px 20px; border-radius: var(--radius-sm);
          font-weight: 600; cursor: pointer; font-size: 0.95rem; display: flex; align-items: center; gap: 8px;
          transition: all 0.2s var(--ease-out);
      }}
      .add-btn:hover {{ background: color-mix(in srgb, var(--primary), black 15%); transform: translateY(-2px); box-shadow: 0 4px 12px color-mix(in srgb, var(--primary), transparent 60%); }}
      .add-btn:active {{ transform: scale(0.95); }}

      /* --- MOBILE --- */
      @media (max-width: 768px) {{
          header {{ height: 35vh; min-height: 260px; border-radius: 0 0 30px 30px; margin-bottom: 20px; }}
          header h1 {{ font-size: 2.2rem; }}
          .header-logo {{ height: 70px; margin-bottom: 15px; }}
          
          .category-nav-wrapper {{ padding: 0 10px; top: 10px; margin-bottom: 25px; }}
          .category-nav {{ padding: 6px; gap: 5px; }}
          .category-nav a {{ padding: 8px 18px; font-size: 0.85rem; }}
          .category-title {{ font-size: 1.6rem; margin-bottom: 20px; }}
          
          .products-grid {{ grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 0 5px; }}
          .product-info {{ padding: 12px; }}
          .product-name {{ font-size: 1rem; margin-bottom: 6px; }}
          .product-desc {{ font-size: 0.75rem; margin-bottom: 10px; -webkit-line-clamp: 2; }}
          .product-price {{ font-size: 1.1rem; }}
          .product-footer {{ padding-top: 10px; }}
          
          .add-btn {{ padding: 0; width: 36px; height: 36px; border-radius: 50%; justify-content: center; }}
          .add-btn span {{ display: none; }}
          .add-btn i {{ font-size: 1rem; }}
          .container {{ padding: 0 10px; }}
      }}

      /* --- FLOATING BUTTON --- */
      #cart-toggle {{
          position: fixed; bottom: 30px; right: 30px; width: 70px; height: 70px;
          background: var(--primary); color: white; border-radius: 50%; border: none;
          box-shadow: var(--shadow-float); cursor: pointer; z-index: 99;
          display: flex; justify-content: center; align-items: center; 
          transition: transform 0.3s var(--ease-bounce);
      }}
      #cart-toggle:hover {{ transform: scale(1.1) rotate(5deg); }}
      #cart-toggle i {{ font-size: 1.8rem; }}
      #cart-count {{ 
          position: absolute; top: -2px; right: -2px; background: #ff3b30; color: white;
          width: 26px; height: 26px; border-radius: 50%; font-size: 0.85rem; font-weight: 800; 
          display: flex; align-items: center; justify-content: center; border: 2px solid white;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      }}

      /* --- SIDEBAR (QR SPECIFIC) --- */
      #cart-sidebar {{
          position: fixed; top: 0; right: -100%; width: 100%; max-width: 450px; height: 100%;
          z-index: 1000; display: flex; flex-direction: column; transition: right 0.5s var(--ease-out);
          box-shadow: -10px 0 50px rgba(0,0,0,0.2); background: white;
      }}
      #cart-sidebar.open {{ right: 0; }}
      @media (max-width: 768px) {{ #cart-sidebar {{ max-width: 100%; }} }}
      
      .cart-content-wrapper {{ height: 100%; display: flex; flex-direction: column; background: var(--surface-glass); backdrop-filter: blur(30px); }}
      
      .sidebar-header-row {{
          padding: 20px 25px; background: rgba(255,255,255,0.5); border-bottom: 1px solid var(--border-light);
          display: flex; flex-direction: column; gap: 15px;
      }}
      .sidebar-top {{ display: flex; justify-content: space-between; align-items: center; }}
      
      /* Tabs in Sidebar */
      .sidebar-tabs {{ display: flex; background: #f1f5f9; padding: 4px; border-radius: 12px; }}
      .sb-tab {{ 
          flex: 1; text-align: center; padding: 10px; cursor: pointer; font-weight: 600; color: #64748b;
          border-radius: 8px; transition: all 0.2s; border: none; background: transparent;
      }}
      .sb-tab.active {{ background: white; color: var(--primary); box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}

      .sidebar-scroll-area {{ flex-grow: 1; overflow-y: auto; padding: 20px; }}
      
      /* Cart Item */
      .cart-item {{ 
          display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; 
          padding: 15px; background: white; border-radius: 16px; box-shadow: var(--shadow-sm); 
          border: 1px solid transparent; transition: border 0.2s;
      }}
      .cart-item-info {{ flex-grow: 1; padding-right: 10px; }}
      .cart-item-name {{ font-weight: 700; font-size: 1rem; display: block; margin-bottom: 4px; }}
      .cart-item-mods {{ font-size: 0.85rem; color: #888; display: block; }}
      .cart-item-price {{ color: var(--primary); font-weight: 800; font-size: 1rem; margin-top: 6px; display: block; }}
      .qty-control {{ display: flex; gap: 10px; background: #f1f5f9; padding: 5px; border-radius: 10px; align-items: center; }}
      .qty-btn {{ width: 30px; height: 30px; background: white; border-radius: 8px; border: none; font-weight: 700; box-shadow: var(--shadow-sm); cursor: pointer; }}
      
      /* History Item */
      .history-card {{
          background: white; border-radius: 16px; padding: 20px; margin-bottom: 15px;
          box-shadow: var(--shadow-sm); border: 1px solid var(--border-light);
      }}
      .h-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
      .status-badge {{ padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }}
      .st-new {{ background: var(--st-new-bg); color: var(--st-new-text); }}
      .st-work {{ background: var(--st-work-bg); color: var(--st-work-text); }}
      .st-ready {{ background: var(--st-ready-bg); color: var(--st-ready-text); }}
      .st-done {{ background: var(--st-done-bg); color: var(--st-done-text); }}
      
      .cart-footer {{ padding: 25px; background: white; box-shadow: 0 -10px 40px rgba(0,0,0,0.05); }}
      .total-row {{ display: flex; justify-content: space-between; font-size: 1.3rem; font-weight: 800; margin-bottom: 20px; color: var(--text-main); }}
      
      .main-btn {{ 
          width: 100%; padding: 16px; background: var(--primary); color: white; border: none; 
          border-radius: var(--radius-md); font-size: 1.1rem; font-weight: 700; cursor: pointer;
          display: flex; justify-content: center; align-items: center; gap: 10px; box-shadow: 0 8px 20px color-mix(in srgb, var(--primary), transparent 60%);
      }}
      .main-btn:active {{ transform: scale(0.98); }}
      .main-btn:disabled {{ background: #e2e8f0; color: #94a3b8; cursor: not-allowed; box-shadow: none; transform: none; }}
      .main-btn.secondary {{ background: #f1f5f9; color: #333; margin-top: 10px; box-shadow: none; }}

      /* --- MODALS --- */
      .modal-overlay {{
          position: fixed; top: 0; left: 0; width: 100%; height: 100%;
          background: rgba(0,0,0,0.6); backdrop-filter: blur(8px);
          z-index: 2000; display: none; justify-content: center; align-items: center; opacity: 0; transition: opacity 0.3s;
      }}
      .modal-overlay.visible {{ display: flex; opacity: 1; }}
      .modal-content {{
          background: #fff; padding: 30px; border-radius: 28px; width: 90%; max-width: 500px;
          max-height: 90vh; overflow-y: auto; transform: translateY(20px); transition: transform 0.3s;
          box-shadow: var(--shadow-lg);
      }}
      .modal-overlay.visible .modal-content {{ transform: translateY(0); }}
      
      /* Product Detail Modal */
      .product-detail-img {{ width: 100%; aspect-ratio: 16/9; object-fit: cover; border-radius: 18px; margin-bottom: 20px; box-shadow: var(--shadow-sm); }}
      .detail-title {{ font-size: 1.8rem; font-weight: 800; margin-bottom: 10px; line-height: 1.2; }}
      .detail-price {{ font-size: 1.5rem; color: var(--primary); font-weight: 800; margin-bottom: 20px; }}
      .detail-desc {{ color: #64748b; font-size: 1rem; line-height: 1.6; margin-bottom: 25px; }}
      
      /* Modifiers */
      #detail-modifiers {{ margin-bottom: 30px; border-top: 1px solid #f1f5f9; padding-top: 15px; }}
      .mod-detail-item {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f1f5f9; cursor: pointer; }}
      .mod-detail-item label {{ display: flex; align-items: center; width: 100%; cursor: pointer; }}
      .mod-detail-checkbox {{ width: 22px; height: 22px; margin-right: 15px; accent-color: var(--primary); cursor: pointer; }}
      .mod-detail-name {{ font-weight: 600; font-size: 1rem; color: var(--text-main); flex-grow: 1; }}
      .mod-detail-price {{ font-weight: 700; color: var(--primary); font-size: 0.95rem; }}
      
      /* Footer */
      footer {{ background: var(--footer-bg); color: var(--footer-text); padding: 80px 20px 40px; margin-top: auto; }}
      .footer-grid {{ display: grid; gap: 30px; max-width: 1000px; margin: 0 auto; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
      .footer-link {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; color: inherit; text-decoration: none; opacity: 0.85; font-size: 1.05rem; }}
      .socials a {{ display: inline-flex; width: 45px; height: 45px; background: rgba(255,255,255,0.15); border-radius: 12px; justify-content: center; align-items: center; color: white; font-size: 1.3rem; margin-right: 10px; }}
      
      .pay-option {{ padding: 15px; border: 2px solid #e2e8f0; border-radius: 12px; margin-bottom: 10px; cursor: pointer; display: flex; align-items: center; gap: 15px; font-weight: 600; transition: all 0.2s; }}
      .pay-option:hover {{ border-color: var(--primary); background: #f8faff; }}
      
      .spinner {{ width: 24px; height: 24px; border: 3px solid rgba(0,0,0,0.1); border-top: 3px solid var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; }}
      @keyframes spin {{ 100% {{ transform: rotate(360deg); }} }}
      @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    </style>
</head>
<body>
    <header>
        <div class="header-bg"></div>
        <div class="header-content">
            <div class="header-logo-container">{logo_html}</div>
            <h1>{site_header_text}</h1>
            <div class="table-badge"><i class="fa-solid fa-chair"></i> {table_name}</div>
        </div>
    </header>
    
    <div class="category-nav-wrapper">
        <nav class="category-nav" id="category-nav"></nav>
    </div>
    
    <div class="container">
        <main id="menu">
            <div style="text-align:center; padding: 80px;"><div class="spinner" style="margin:0 auto;"></div></div>
        </main>
    </div>

    <button id="cart-toggle">
        <i class="fa-solid fa-utensils"></i>
        <span id="cart-count">0</span>
    </button>

    <aside id="cart-sidebar">
        <div class="cart-content-wrapper">
            <div class="sidebar-header-row">
                <div class="sidebar-top">
                    <h3 style="margin:0; font-size:1.5rem;">Замовлення</h3>
                    <button id="close-cart-btn" style="background:none; border:none; font-size:1.8rem; cursor:pointer; color: #94a3b8;">&times;</button>
                </div>
                <div class="sidebar-tabs">
                    <button class="sb-tab active" onclick="switchTab('cart')">Кошик</button>
                    <button class="sb-tab" onclick="switchTab('history')">Історія</button>
                </div>
            </div>
            
            <div id="view-cart" class="sidebar-scroll-area">
                <div id="cart-items-container"></div>
            </div>
            
            <div id="view-history" class="sidebar-scroll-area" style="display:none;">
                <div id="history-items-container"></div>
            </div>
            
            <div class="cart-footer">
                <div class="total-row">
                    <span id="total-label">Разом:</span>
                    <span id="cart-total-price">0.00 грн</span>
                </div>
                
                <div id="cart-actions">
                    <button id="place-order-btn" class="main-btn" disabled>
                        <span>Замовити</span> <i class="fa-solid fa-arrow-right"></i>
                    </button>
                    <button id="call-waiter-btn" class="main-btn secondary"><i class="fa-solid fa-bell"></i> Викликати офіціанта</button>
                </div>
                
                <div id="history-actions" style="display:none;">
                    <button id="request-bill-btn" class="main-btn" style="background:#1e293b;">
                        <i class="fa-solid fa-receipt"></i> Попросити рахунок
                    </button>
                    <button onclick="switchTab('cart')" class="main-btn secondary">Додати ще страв</button>
                </div>
            </div>
        </div>
    </aside>

    <div id="product-modal" class="modal-overlay">
        <div class="modal-content">
            <div style="position:relative;">
                <button class="close-modal" style="position:absolute; top:-10px; right:-10px; background:white; border-radius:50%; width:35px; height:35px; border:none; box-shadow:0 2px 10px rgba(0,0,0,0.1); font-size:1.5rem; cursor:pointer;">&times;</button>
                <img src="" id="det-img" class="product-detail-img">
                <h2 id="det-name" class="detail-title"></h2>
                <div id="det-desc" class="detail-desc"></div>
                <div id="det-price" class="detail-price"></div>
                
                <div id="detail-modifiers"></div>
                
                <button id="det-add-btn" class="main-btn">В кошик</button>
            </div>
        </div>
    </div>

    <div id="pay-modal" class="modal-overlay">
        <div class="modal-content">
            <h3 style="margin-top:0;">Спосіб оплати</h3>
            <p style="color:#666; margin-bottom:20px;">Як бажаєте розрахуватись?</p>
            <div class="pay-option" onclick="sendBillRequest('cash')">
                <i class="fa-solid fa-money-bill-wave" style="color:#2e7d32; font-size:1.5rem;"></i> Готівка
            </div>
            <div class="pay-option" onclick="sendBillRequest('card')">
                <i class="fa-regular fa-credit-card" style="color:#1565c0; font-size:1.5rem;"></i> Картка / Термінал
            </div>
            <button class="main-btn secondary close-modal" style="margin-top:20px;">Скасувати</button>
        </div>
    </div>

    <div id="success-modal" class="modal-overlay">
        <div class="modal-content" style="text-align:center;">
            <div style="width:70px; height:70px; background:#dcfce7; border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px;">
                <i class="fa-solid fa-check" style="color:#16a34a; font-size:35px;"></i>
            </div>
            <h3 id="success-title" style="margin-bottom:10px; font-size:1.5rem;">Успішно!</h3>
            <p id="success-msg" style="color:#64748b; margin-bottom:25px; font-size:1rem;"></p>
            <button class="main-btn close-modal">Гаразд</button>
        </div>
    </div>

    <div id="page-modal" class="modal-overlay">
        <div class="modal-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; padding-bottom:15px; border-bottom:1px solid #f1f5f9;">
                <h3 id="page-title" style="margin:0; font-size:1.5rem;"></h3>
                <span class="close-modal" style="font-size:1.8rem; cursor:pointer; color:#cbd5e1;">&times;</span>
            </div>
            <div id="page-body" class="page-content-body" style="line-height:1.7; color:#334155;"></div>
        </div>
    </div>

    <footer>
        <div class="footer-grid">
            <div class="footer-col">
                <h4>Контакти</h4>
                <div class="footer-link"><i class="fa-solid fa-location-dot"></i> {footer_address}</div>
                <a href="tel:{footer_phone}" class="footer-link"><i class="fa-solid fa-phone"></i> {footer_phone}</a>
                <div class="footer-link"><i class="fa-regular fa-clock"></i> {working_hours}</div>
            </div>
            <div class="footer-col">
                <h4>Інформація</h4>
                {menu_links_html}
            </div>
            <div class="footer-col">
                <h4>Wi-Fi</h4>
                <div class="footer-link"><i class="fa-solid fa-wifi"></i> {wifi_ssid}</div>
                <div class="footer-link"><i class="fa-solid fa-lock"></i> {wifi_password}</div>
            </div>
            <div class="footer-col">
                <h4>Соцмережі</h4>
                <div class="socials">{social_links_html}</div>
            </div>
        </div>
        <div style="text-align:center; margin-top:60px; opacity:0.4; font-size:0.85rem;">
            &copy; 2024 {site_title}. All rights reserved.
        </div>
    </footer>

    <script>
        const TABLE_ID = {table_id};
        const MENU = {menu_data};
        let HISTORY = {history_data};
        let GRAND_TOTAL = {grand_total};
        let cart = {{}};
        
        let currentDetailProduct = null;
        let ws = null; // WebSocket variable

        document.addEventListener('DOMContentLoaded', () => {{
            // Restore cart
            try {{
                const saved = localStorage.getItem('qrCart');
                if (saved) {{
                    const parsed = JSON.parse(saved);
                    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {{
                        cart = parsed;
                    }}
                }}
            }} catch (e) {{ cart = {{}}; }}

            renderMenu();
            updateCartView();
            initListeners();
            
            // Initial fetch
            fetchUpdates(); 
            
            // WebSocket connection for live updates
            connectTableWebSocket();
        }});

        function connectTableWebSocket() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${{protocol}}//${{window.location.host}}/ws/table/${{TABLE_ID}}`;
            
            if (ws && ws.readyState === WebSocket.OPEN) return;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {{ console.log("Table WS Connected"); }};

            ws.onmessage = (event) => {{
                try {{
                    const data = JSON.parse(event.data);
                    if (data.type === 'order_update') {{
                        // При обновлении заказа перезапрашиваем историю
                        fetchUpdates();
                    }}
                }} catch (e) {{ console.error("WS Parse Error", e); }}
            }};

            ws.onclose = () => {{
                console.log("WS Closed. Reconnecting...");
                setTimeout(connectTableWebSocket, 3000);
            }};
            
            ws.onerror = (err) => {{
                console.error("WS Error:", err);
                ws.close();
            }};
        }}

        function initListeners() {{
            // Sidebar
            const sidebar = document.getElementById('cart-sidebar');
            document.getElementById('cart-toggle').onclick = () => sidebar.classList.add('open');
            document.getElementById('close-cart-btn').onclick = () => sidebar.classList.remove('open');
            
            // Modals
            document.querySelectorAll('.close-modal').forEach(b => {{
                b.onclick = (e) => e.target.closest('.modal-overlay').classList.remove('visible');
            }});

            // Actions
            document.getElementById('place-order-btn').onclick = placeOrder;
            document.getElementById('call-waiter-btn').onclick = callWaiter;
            document.getElementById('request-bill-btn').onclick = () => document.getElementById('pay-modal').classList.add('visible');
            
            // Add to cart from modal
            document.getElementById('det-add-btn').onclick = () => {{
                const selectedMods = [];
                document.querySelectorAll('.mod-detail-checkbox:checked').forEach(cb => {{
                    selectedMods.push({{
                        id: parseInt(cb.value),
                        name: cb.dataset.name,
                        price: parseFloat(cb.dataset.price)
                    }});
                }});
                addToCart(currentDetailProduct, selectedMods);
                document.getElementById('product-modal').classList.remove('visible');
            }};

            // Page links
            document.body.addEventListener('click', (e) => {{
                const link = e.target.closest('.menu-popup-trigger');
                if(link) {{
                    e.preventDefault();
                    openPageModal(link.dataset.itemId, link.innerText);
                }}
            }});
        }}

        // --- TABS LOGIC ---
        window.switchTab = (tab) => {{
            document.querySelectorAll('.sb-tab').forEach(b => b.classList.remove('active'));
            document.querySelector(`.sb-tab[onclick="switchTab('${{tab}}')"]`).classList.add('active');
            
            document.getElementById('view-cart').style.display = tab === 'cart' ? 'block' : 'none';
            document.getElementById('view-history').style.display = tab === 'history' ? 'block' : 'none';
            
            document.getElementById('cart-actions').style.display = tab === 'cart' ? 'block' : 'none';
            document.getElementById('history-actions').style.display = tab === 'history' ? 'block' : 'none';
            
            updateFooterTotal(tab);
        }};

        function updateFooterTotal(tab) {{
            const label = document.getElementById('total-label');
            const totalEl = document.getElementById('cart-total-price');
            
            const cartItems = Object.values(cart);
            const cartSum = cartItems.reduce((s, i) => s + (i.price * i.quantity), 0);
            
            if (tab === 'cart') {{
                label.innerText = 'Разом (Кошик):';
                totalEl.innerText = cartSum.toFixed(2) + ' грн';
            }} else {{
                label.innerText = 'До сплати (Всього):';
                totalEl.innerText = (GRAND_TOTAL + cartSum).toFixed(2) + ' грн';
            }}
        }}

        // --- MENU RENDER ---
        function renderMenu() {{
            const main = document.getElementById('menu');
            const nav = document.getElementById('category-nav');
            main.innerHTML = ''; nav.innerHTML = '';

            MENU.categories.forEach((cat, idx) => {{
                const link = document.createElement('a');
                link.href = `#c-${{cat.id}}`;
                link.textContent = cat.name;
                if(idx===0) link.classList.add('active');
                nav.appendChild(link);

                const section = document.createElement('div');
                section.id = `c-${{cat.id}}`;
                section.className = 'category-section';
                section.innerHTML = `<h2 class="category-title">${{cat.name}}</h2>`;

                const grid = document.createElement('div');
                grid.className = 'products-grid';

                const products = MENU.products.filter(p => p.category_id === cat.id);
                if (products.length > 0) {{
                    products.forEach(prod => {{
                        const card = document.createElement('div');
                        card.className = 'product-card';
                        const img = prod.image_url ? `/${{prod.image_url}}` : '/static/images/placeholder.jpg';
                        const prodJson = JSON.stringify(prod).replace(/"/g, '&quot;');
                        
                        card.onclick = (e) => {{
                            if(!e.target.closest('.add-btn')) openDetail(prod);
                        }};

                        card.innerHTML = `
                            <div class="product-image-wrapper"><img src="${{img}}" class="product-image" loading="lazy"></div>
                            <div class="product-info">
                                <div class="product-header">
                                    <div class="product-name">${{prod.name}}</div>
                                    <div class="product-desc">${{prod.description||''}}</div>
                                </div>
                                <div class="product-footer">
                                    <div class="product-price">${{prod.price}} грн</div>
                                    <button class="add-btn" onclick="event.stopPropagation(); handleAdd(this, JSON.parse(this.dataset.product))" data-product="${{prodJson}}">
                                        <i class="fa-solid fa-plus"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                        grid.appendChild(card);
                    }});
                    section.appendChild(grid);
                    main.appendChild(section);
                }}
            }});
            setupScrollSpy();
        }}

        // --- ACTIONS ---
        window.handleAdd = (btn, prod) => {{
            if(prod.modifiers && prod.modifiers.length > 0) {{
                openDetail(prod);
            }} else {{
                addToCart(prod, []);
                // Animation
                btn.style.background = '#22c55e';
                const i = btn.querySelector('i');
                i.className = 'fa-solid fa-check';
                setTimeout(() => {{ 
                    btn.style.background = ''; i.className = 'fa-solid fa-plus'; 
                }}, 1000);
            }}
        }};

        function openDetail(prod) {{
            currentDetailProduct = prod;
            document.getElementById('det-img').src = prod.image_url ? `/${{prod.image_url}}` : '/static/images/placeholder.jpg';
            document.getElementById('det-name').innerText = prod.name;
            document.getElementById('det-desc').innerText = prod.description || '';
            
            const modContainer = document.getElementById('detail-modifiers');
            modContainer.innerHTML = '';
            
            if(prod.modifiers && prod.modifiers.length > 0) {{
                modContainer.innerHTML = '<p style="font-weight:600;color:#64748b;margin-bottom:10px;">Добавки:</p>';
                prod.modifiers.forEach(m => {{
                    modContainer.innerHTML += `
                    <div class="mod-detail-item">
                        <label>
                            <input type="checkbox" class="mod-detail-checkbox" value="${{m.id}}" data-price="${{m.price}}" data-name="${{m.name}}" onchange="updateDetailPrice()">
                            <span class="mod-detail-name">${{m.name}}</span>
                            <span class="mod-detail-price">+${{m.price}} грн</span>
                        </label>
                    </div>`;
                }});
            }}
            
            updateDetailPrice();
            document.getElementById('product-modal').classList.add('visible');
        }}
        
        window.updateDetailPrice = () => {{
            if(!currentDetailProduct) return;
            let price = currentDetailProduct.price;
            document.querySelectorAll('.mod-detail-checkbox:checked').forEach(cb => price += parseFloat(cb.dataset.price));
            document.getElementById('det-price').innerText = price.toFixed(2) + ' грн';
            document.getElementById('det-add-btn').innerText = `В кошик (${{price.toFixed(2)}} грн)`;
        }};

        function addToCart(prod, mods) {{
            const modIds = mods.map(m => m.id).sort().join('-');
            const key = `${{prod.id}}-${{modIds}}`;
            
            if (cart[key]) {{
                cart[key].quantity++;
            }} else {{
                let price = prod.price;
                mods.forEach(m => price += m.price);
                cart[key] = {{
                    id: prod.id, name: prod.name, price: price, quantity: 1, modifiers: mods, key: key
                }};
            }}
            saveCart();
            updateCartView();
            
            // Bounce
            const toggle = document.getElementById('cart-toggle');
            toggle.style.transform = 'scale(1.2)';
            setTimeout(() => toggle.style.transform = 'scale(1)', 200);
        }}

        function updateCartView() {{
            const container = document.getElementById('cart-items-container');
            container.innerHTML = '';
            let count = 0;
            
            const items = Object.values(cart);
            if (items.length === 0) {{
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#999;"><i class="fa-solid fa-utensils" style="font-size:3rem;opacity:0.2;margin-bottom:10px;"></i><p>Кошик порожній</p></div>';
            }} else {{
                items.forEach(item => {{
                    count += item.quantity;
                    const modStr = item.modifiers.map(m => m.name).join(', ');
                    container.innerHTML += `
                    <div class="cart-item">
                        <div class="cart-item-info">
                            <span class="cart-item-name">${{item.name}}</span>
                            <span class="cart-item-mods">${{modStr}}</span>
                            <span class="cart-item-price">${{(item.price * item.quantity).toFixed(2)}} грн</span>
                        </div>
                        <div class="qty-control">
                            <button class="qty-btn" onclick="updateQty('${{item.key}}', -1)">-</button>
                            <span class="qty-val">${{item.quantity}}</span>
                            <button class="qty-btn" onclick="updateQty('${{item.key}}', 1)">+</button>
                        </div>
                    </div>`;
                }});
            }}
            
            document.getElementById('cart-count').innerText = count;
            document.getElementById('cart-count').style.display = count > 0 ? 'flex' : 'none';
            document.getElementById('place-order-btn').disabled = count === 0;
            document.getElementById('place-order-btn').style.opacity = count === 0 ? '0.5' : '1';
            
            updateHistoryView();
        }}

        window.updateQty = (key, delta) => {{
            if (cart[key]) {{
                cart[key].quantity += delta;
                if (cart[key].quantity <= 0) delete cart[key];
                saveCart();
                updateCartView();
            }}
        }};
        
        function saveCart() {{ localStorage.setItem('qrCart', JSON.stringify(cart)); }}

        function updateHistoryView() {{
            const container = document.getElementById('history-items-container');
            container.innerHTML = '';
            
            if (HISTORY.length === 0) {{
                container.innerHTML = '<div style="text-align:center;padding:40px;color:#999;"><i class="fa-solid fa-clock-rotate-left" style="font-size:3rem;opacity:0.2;margin-bottom:10px;"></i><p>Історія порожня</p></div>';
            }} else {{
                HISTORY.forEach(o => {{
                    let stClass = 'st-done';
                    const s = o.status.toLowerCase();
                    if(s.includes('нов')) stClass = 'st-new';
                    else if(s.includes('роб') || s.includes('оброб')) stClass = 'st-work';
                    else if(s.includes('гот')) stClass = 'st-ready';
                    
                    container.innerHTML += `
                    <div class="history-card">
                        <div class="h-header">
                            <span style="font-weight:700;">#${{o.id}}</span>
                            <span class="status-badge ${{stClass}}">${{o.status}}</span>
                        </div>
                        <div style="font-size:0.9rem; color:#444; margin-bottom:10px;">
                            ${{o.products.split(', ').map(p => `<div>• ${{p}}</div>`).join('')}}
                        </div>
                        <div style="display:flex; justify-content:space-between; border-top:1px dashed #eee; padding-top:8px;">
                            <span style="color:#888; font-size:0.85rem;">${{o.time}}</span>
                            <span style="font-weight:800;">${{o.total_price.toFixed(2)}} грн</span>
                        </div>
                    </div>`;
                }});
            }}
            
            const activeTab = document.querySelector('.sb-tab.active').innerText === 'Кошик' ? 'cart' : 'history';
            updateFooterTotal(activeTab);
        }}

        // --- API CALLS ---
        async function placeOrder() {{
            const btn = document.getElementById('place-order-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<div class="spinner"></div>';
            
            try {{
                const items = Object.values(cart).map(i => ({{
                    id: i.id, quantity: i.qty, modifiers: i.modifiers
                }}));
                
                const res = await fetch(`/api/menu/table/${{TABLE_ID}}/place_order`, {{
                    method: 'POST', headers: {{'Content-Type': 'application/json'}}, 
                    body: JSON.stringify(items)
                }});
                
                if(res.ok) {{
                    cart = {{}}; saveCart();
                    await fetchUpdates();
                    switchTab('history');
                    showSuccess('Прийнято!', 'Замовлення відправлено на кухню.');
                }} else {{
                    throw new Error();
                }}
            }} catch(e) {{ 
                alert('Помилка при створенні замовлення.'); 
            }} finally {{ 
                btn.innerHTML = originalHTML;
            }}
        }}

        async function fetchUpdates() {{
            try {{
                const res = await fetch(`/api/menu/table/${{TABLE_ID}}/updates`);
                if(res.ok) {{
                    const data = await res.json();
                    HISTORY = data.history_data;
                    GRAND_TOTAL = data.grand_total;
                    updateCartView(); // re-renders history
                }}
            }} catch(e) {{}}
        }}

        async function callWaiter() {{
            try {{ await fetch(`/api/menu/table/${{TABLE_ID}}/call_waiter`, {{method:'POST'}}); showSuccess('Викликано!', 'Офіціант вже йде.'); }} catch(e){{}}
        }}

        async function sendBillRequest(method) {{
            try {{ 
                await fetch(`/api/menu/table/${{TABLE_ID}}/request_bill?method=${{method}}`, {{method:'POST'}}); 
                document.getElementById('pay-modal').classList.remove('visible');
                showSuccess('Запит надіслано', 'Очікуйте офіціанта з рахунком.');
            }} catch(e){{}}
        }}
        
        function showSuccess(title, msg) {{
            document.getElementById('success-title').innerText = title;
            document.getElementById('success-msg').innerText = msg;
            document.getElementById('success-modal').classList.add('visible');
        }}

        async function openPageModal(id, title) {{
            const modal = document.getElementById('page-modal');
            document.getElementById('page-title').innerText = title;
            document.getElementById('page-body').innerHTML = '<div style="text-align:center; padding:30px;"><div class="spinner" style="border-top-color:#333; margin:0 auto;"></div></div>';
            modal.classList.add('visible');
            try {{
                const res = await fetch('/api/page/'+id);
                const d = await res.json();
                document.getElementById('page-body').innerHTML = d.content;
            }} catch(e) {{ document.getElementById('page-body').innerText = 'Помилка'; }}
        }}

        function setupScrollSpy() {{
            const observer = new IntersectionObserver(entries => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        document.querySelectorAll('.category-nav a').forEach(l => l.classList.remove('active'));
                        const active = document.querySelector(`.category-nav a[href="#${{entry.target.id}}"]`);
                        if(active) {{
                            active.classList.add('active');
                            active.scrollIntoView({{behavior:'smooth', inline:'center', block: 'nearest'}});
                        }}
                    }}
                }});
            }}, {{rootMargin: '-20% 0px -70% 0px'}});
            document.querySelectorAll('.category-section').forEach(s => observer.observe(s));
        }}
    </script>
</body>
</html>
"""